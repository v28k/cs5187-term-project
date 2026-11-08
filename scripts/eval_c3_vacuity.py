#!/usr/bin/env python3
"""C3 evaluation: break TLP-WHERE checks down by vacuity, predicate kind and data synthesis.

Usage (from src/): PYTHONPATH=. python ../scripts/eval_c3_vacuity.py tlp_synth 300
"""
import random, tempfile, sys, collections
from pathlib import Path
from pgfuzz.core.interfaces import Generator, GeneratorContext
from pgfuzz.core.plugins import instantiate
from pgfuzz.runner import load_config
from pgfuzz.cli import _executor_from
def main():
    cfgp='configs/eval/c3_duckdb.yaml'; arm=sys.argv[1]; n=int(sys.argv[2])
    cfg=load_config(cfgp); fc=[c for c in cfg.configs if c.name==arm][0]
    gen=instantiate(fc.generator.plugin, Generator, fc.generator.render(**cfg.substitutions(fc.name,0,0)))
    gen.setup(GeneratorContext(7, random.Random(7), Path(tempfile.mkdtemp())))
    ex=_executor_from(cfgp, fc.name); ex.start()
    cat=collections.Counter(); shown=0
    try:
      for i in range(n):
        tc=gen.next_testcase(); res=ex.execute(tc)
        k=int(tc.meta.get('synth',0))
        for c in tc.meta.get('checks',[]):
          st=res.statements[c['stmt']] if c['stmt']<len(res.statements) else None
          for r in (getattr(st,'checks',None) or []):
            if r.get('kind')!='tlp_where' or r.get('status')!='ok' or not r.get('partitions'): continue
            parts=r['partitions']; vac=sum(1 for x in parts if x)<2
            constpred = not any(ch.isalpha() and ch not in 'TRUEFALSNtruefalsn' for ch in (c.get('pred') or ''))
            cols = '.' in (c.get('pred') or '')
            key=('vacuous' if vac else 'ok', 'cols' if cols else 'nocols', 'synth' if k else 'nosynth')
            cat[key]+=1
            if vac and cols and shown<6:
              shown+=1; print('---', parts, 'lhs_rows', r.get('lhs_rows'), 'synth', k); print('PRED', c['pred'][:200]); print('SQL', tc.statements[c['stmt']][:400])
    finally: ex.stop()
    for kk,v in sorted(cat.items()): print(kk,v)

if __name__ == '__main__':
    main()
