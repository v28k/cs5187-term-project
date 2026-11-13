"""Dialect overlays: adapt one portable grammar to an engine without copying it.

An overlay is a ``.pgg`` file whose lines may start with a directive; everything else is
ordinary grammar text that is appended (rules with an existing name add alternatives).

Directives (one per line; strings are double-quoted, ``*`` means "every alternative")::

    %drop     rule "substring"         remove top-level alternatives of ``rule`` whose
                                       source text contains the substring
    %dropopt  rule "substring"         remove alternatives *inside groups* ``( a | b )`` of
                                       ``rule`` whose text contains the substring
    %droprule rule                     remove a rule entirely (and, by cascade, every
                                       alternative that uses it)
    %droptype T                        remove type ``T``: its ``%type`` line, the variants
                                       declared for it and every alternative that names it
    %replace  rule "old" "new"         textual replacement inside ``rule``'s variants
    %weight   rule "substring" W       set the weight of matching top-level alternatives
    %addclass T cls / %delclass T cls  add / remove type ``T`` to / from type class ``cls``

Removals cascade: an alternative that refers to a rule which no longer exists is removed
too, and a variant without alternatives disappears. :func:`apply_overlays` returns the
edited grammar text plus a report of every edit (used for the "mined vs manual overlay
lines" measurement of RQ1).
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

from pgfuzz.grammar.dsl import Alt, Builtin, Group, GrammarError, NT, Repeat, Variant, _Parser, parse_grammar

DIRECTIVES = ("%drop", "%dropopt", "%droprule", "%droptype", "%replace", "%weight", "%addclass", "%delclass")


@dataclass
class OverlayReport:
    dropped: list[str] = field(default_factory=list)       # "rule: alt text"
    replaced: list[str] = field(default_factory=list)
    cascaded: list[str] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)      # directives that matched nothing
    added_lines: int = 0
    directive_lines: int = 0

    def summary(self) -> dict[str, int]:
        return {"dropped": len(self.dropped), "replaced": len(self.replaced), "cascaded": len(self.cascaded),
                "unmatched": len(self.unmatched), "added_lines": self.added_lines,
                "directive_lines": self.directive_lines}


@dataclass
class _Site:
    alt: Alt
    siblings: list[Alt]
    owner: object                 # Variant or Group
    parent: "_Site | None"        # enclosing alternative for group alternatives
    rule: str
    elem_index: int = -1          # index of the owning group's element in the parent alternative
    optional: bool = False        # owning group is wrapped in x? / x* / x{0,n}


def _group_of(el: object) -> tuple[Group | None, bool]:
    """The group an element wraps (directly or inside repetitions) and whether it is optional."""
    optional = False
    while isinstance(el, Repeat):
        optional = optional or el.lo == 0
        el = el.elem
    return (el, optional) if isinstance(el, Group) else (None, optional)


def _sites(variants: list[Variant]) -> list[_Site]:
    out: list[_Site] = []

    def visit(site: _Site) -> None:
        out.append(site)
        for i, el in enumerate(site.alt.elems):
            g, opt = _group_of(el)
            if g is not None:
                for a in g.alts:
                    visit(_Site(a, g.alts, g, site, site.rule, i, opt))

    for v in variants:
        for a in v.alts:
            visit(_Site(a, v.alts, v, None, v.name))
    return out


def _direct_refs(el: object) -> tuple[set[str], set[str]]:
    """Rules and types an element names, not looking inside groups."""
    rules: set[str] = set()
    types: set[str] = set()
    while isinstance(el, Repeat):
        el = el.elem
    if isinstance(el, NT):
        rules.add(el.name)
        if el.targ is not None and el.targ.name:
            types.add(el.targ.name)
        if el.targ is not None and el.targ.cls:
            types.add("class:" + el.targ.cls)
    elif isinstance(el, Builtin):
        for x in el.args:
            types.add(x.split(":")[0])
            if ":" in x:
                types.add("class:" + x.split(":", 1)[1])
    return rules, types


def _optional(el: object) -> bool:
    return isinstance(el, Repeat) and el.lo == 0


def _parse_directives(text: str) -> tuple[list[list[str]], str, int]:
    """Split overlay text into directives (tokenised) and ordinary grammar text."""
    directives, rest = [], []
    for line in text.splitlines():
        s = line.strip()
        if s.split(" ", 1)[0] in DIRECTIVES:
            body = s.split("#", 1)[0] if '"' not in s else s
            try:
                toks = shlex.split(body, comments=False)
            except ValueError as e:
                raise GrammarError(f"overlay: bad directive {s!r}: {e}") from e
            directives.append(toks)
            rest.append("")          # keep line numbers stable
        else:
            rest.append(line)
    return directives, "\n".join(rest), len(directives)


class _Editor:
    def __init__(self, text: str) -> None:
        self.text = text
        _types, self.variants, _attrs, _start = _Parser(text).parse()
        self.sites = _sites(self.variants)
        self.drop: set[int] = set()                    # alt uids to remove
        self.drop_elems: set[tuple[int, int]] = set()  # (alt uid, element index) to remove
        self.drop_variants: set[int] = set()           # id(variant)
        self.replacements: list[tuple[int, int, str]] = []

    def alt_text(self, a: Alt) -> str:
        return self.text[a.span[0]:a.span[1]]

    def mark(self, site: _Site, report: list[str], why: str = "") -> None:
        """Remove an alternative. A group left empty disappears if it was optional, else the
        enclosing alternative goes; a variant left empty disappears."""
        if site.alt.uid in self.drop:
            return
        self.drop.add(site.alt.uid)
        report.append(f"{site.rule}: {self.alt_text(site.alt)[:120]}{why}")
        if all(a.uid in self.drop for a in site.siblings):
            if isinstance(site.owner, Variant):
                self.drop_variants.add(id(site.owner))
            elif site.parent is not None:
                if site.optional:
                    self.drop_elems.add((site.parent.alt.uid, site.elem_index))
                else:
                    self.mark(site.parent, report, " (group emptied)")

    def drop_element(self, site: _Site, idx: int, report: list[str], why: str) -> None:
        if (site.alt.uid, idx) not in self.drop_elems:
            self.drop_elems.add((site.alt.uid, idx))
            s, e = site.alt.elem_spans[idx]
            report.append(f"{site.rule}: element {self.text[s:e][:80]}{why}")

    def render_alt(self, a: Alt) -> str:
        """Text of ``a`` without dropped elements and dropped group alternatives."""
        out, pos = [], a.span[0]
        for i, el in enumerate(a.elems):
            s, e = a.elem_spans[i]
            out.append(self.text[pos:s])
            pos = e
            if (a.uid, i) in self.drop_elems:
                continue
            g, _ = _group_of(el)
            if g is None:
                out.append(self.text[s:e])
                continue
            gs, ge = g.alts[0].span[0], g.alts[-1].span[1]
            out.append(self.text[s:gs])
            out.append(" | ".join(self.render_alt(k) for k in g.alts if k.uid not in self.drop))
            out.append(self.text[ge:e])
        out.append(self.text[pos:a.span[1]])
        return "".join(out)

    def apply(self) -> str:
        if self.replacements:
            eds = sorted(self.replacements)
            for (_s1, e1, _), (s2, _e2, _) in zip(eds, eds[1:]):
                if s2 < e1:
                    raise GrammarError("overlay: overlapping replacements in one directive")
            t = self.text
            for s, e, new in reversed(eds):
                t = t[:s] + new + t[e:]
            return t
        t, pos, out = self.text, 0, []
        for v in self.variants:
            if id(v) in self.drop_variants:
                out.append(t[pos:v.span[0]])
                pos = v.span[1]
                continue
            s, e = v.alts[0].span[0], v.alts[-1].span[1]
            out.append(t[pos:s])
            out.append(" | ".join(self.render_alt(a) for a in v.alts if a.uid not in self.drop))
            pos = e
        out.append(t[pos:])
        return "".join(out)


def _class_edit(text: str, op: str, t: str, cls: str, rep: OverlayReport) -> str:
    pat = re.compile(rf'^(\s*%type\s+{re.escape(t)}\s+"[^"]*")([^\n]*)$', re.M)
    m = pat.search(text)
    if not m:
        rep.unmatched.append(f"{op} {t} {cls}")
        return text
    words = m.group(2).split()
    classes = [w for w in words if "=" not in w]
    rest = [w for w in words if "=" in w]
    if op == "%addclass" and cls not in classes:
        classes.append(cls)
    elif op == "%delclass":
        classes = [c for c in classes if c != cls]
    rep.replaced.append(f"{op} {t} {cls}")
    return text[:m.start()] + m.group(1) + " " + " ".join(classes + rest) + text[m.end():]


def _one_directive(text: str, d: list[str], rep: OverlayReport) -> str:
    if d[0] in ("%addclass", "%delclass"):
        return _class_edit(text, d[0], d[1], d[2], rep)
    ed = _Editor(text)
    op, args = d[0], d[1:]
    hit = False
    if op in ("%drop", "%dropopt", "%weight"):
        if len(args) < (3 if op == "%weight" else 2):
            raise GrammarError(f"overlay: {op} needs arguments: {' '.join(d)}")
        rule, sub = args[0], args[1]
        for site in ed.sites:
            top = site.parent is None
            if site.rule != rule or (op == "%dropopt") == top:
                continue
            if sub == "*" or sub in ed.alt_text(site.alt):
                hit = True
                if op == "%weight":
                    a = site.alt
                    t = ed.alt_text(a)
                    t2 = re.sub(r"^<\s*[\d.]+", f"<{args[2]}", t) if t.startswith("<") else f"<{args[2]}> {t}"
                    ed.replacements.append((a.span[0], a.span[1], t2))
                else:
                    ed.mark(site, rep.dropped)
    elif op == "%droprule":
        for v in ed.variants:
            if v.name == args[0]:
                hit = True
                ed.drop_variants.add(id(v))
                rep.dropped.append(f"{v.name}: <rule>")
    elif op == "%droptype":
        t = args[0]
        hit = bool(re.search(rf"^\s*%type\s+{re.escape(t)}\b", text, re.M))
        for v in ed.variants:
            if v.concrete == t:
                hit = True
                ed.drop_variants.add(id(v))
                rep.dropped.append(f"{v.name}<{t}>: <variant>")
        for site in ed.sites:
            for i, el in enumerate(site.alt.elems):
                if t in _direct_refs(el)[1]:
                    hit = True
                    if _optional(el):
                        ed.drop_element(site, i, rep.dropped, f" (type {t})")
                    else:
                        ed.mark(site, rep.dropped, f" (type {t})")
                        break
    elif op == "%replace":
        rule, old, new = args[0], args[1], args[2]
        for v in ed.variants:
            if v.name == rule:
                seg = text[v.span[0]:v.span[1]]
                if old in seg:
                    hit = True
                    ed.replacements.append((v.span[0], v.span[1], seg.replace(old, new)))
                    rep.replaced.append(f"{rule}: {old!r} -> {new!r}")
    else:
        raise GrammarError(f"overlay: unknown directive {op}")
    if not hit:
        rep.unmatched.append(" ".join(d))
    out = ed.apply()
    if op == "%droptype":
        out = re.sub(rf"^\s*%type\s+{re.escape(args[0])}\b[^\n]*$", "", out, flags=re.M)
    return out


def _directive_pass(text: str, directives: list[list[str]], rep: OverlayReport) -> str:
    for d in directives:
        text = _one_directive(text, d, rep)
    return text


def _cascade(text: str, rep: OverlayReport, max_rounds: int = 50) -> str:
    """Remove alternatives that refer to rules or types that no longer exist."""
    for _ in range(max_rounds):
        types_decl = set(re.findall(r"^\s*%type\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.M))
        ed = _Editor(text)
        defined = {v.name for v in ed.variants}
        changed = False
        classes_decl = set()
        for m in re.finditer(r'^\s*%type\s+\S+\s+"[^"]*"([^\n]*)$', text, re.M):
            classes_decl |= {w for w in m.group(1).split() if "=" not in w}
        for site in ed.sites:
            for i, el in enumerate(site.alt.elems):
                rules_ref, types_ref = _direct_refs(el)
                missing = rules_ref - defined
                missing |= {t for t in types_ref if t.startswith("class:") and t[6:] not in classes_decl}
                if not missing:
                    continue
                changed = True
                if _optional(el):
                    ed.drop_element(site, i, rep.cascaded, f" (needs {', '.join(sorted(missing))})")
                else:
                    ed.mark(site, rep.cascaded, f" (needs {', '.join(sorted(missing))})")
                    break
        for v in ed.variants:
            if v.concrete is not None and v.concrete not in types_decl and id(v) not in ed.drop_variants:
                # concrete may also be a class name; only drop if it is neither
                classes = set(re.findall(r"^\s*%type\s+\S+\s+\"[^\"]*\"([^\n]*)$", text, re.M))
                cls_words = {w for c in classes for w in c.split() if "=" not in w}
                if v.concrete not in cls_words:
                    ed.drop_variants.add(id(v))
                    rep.cascaded.append(f"{v.name}<{v.concrete}>: <variant, type gone>")
                    changed = True
        if not changed:
            return text
        text = ed.apply()
    raise GrammarError("overlay cascade did not converge")


def apply_overlays(base_text: str, overlays: list[str], source: str = "") -> tuple[str, OverlayReport]:
    """Apply overlay texts to ``base_text``; returns (grammar text, report)."""
    rep = OverlayReport()
    text = base_text
    for ov in overlays:
        directives, extra, n = _parse_directives(ov)
        rep.directive_lines += n
        rep.added_lines += sum(1 for ln in extra.splitlines() if ln.strip() and not ln.strip().startswith("#"))
        if directives:
            text = _directive_pass(text, directives, rep)
        text = text + "\n# ---- overlay\n" + extra
        text = _cascade(text, rep)
    parse_grammar(text, source)   # raises if the result is not a valid grammar
    return text, rep


def load_with_overlays(base: str | Path, overlays: list[str | Path]) -> tuple[str, OverlayReport]:
    return apply_overlays(Path(base).read_text(encoding="utf-8"),
                          [Path(o).read_text(encoding="utf-8") for o in overlays], str(base))
