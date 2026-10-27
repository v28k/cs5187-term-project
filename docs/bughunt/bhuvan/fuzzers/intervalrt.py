"""interval text round trip under every IntervalStyle; exact field comparison.
usage: intervalrt.py PORT N SEED
"""
import sys, random
import psycopg

STYLES = ["postgres", "postgres_verbose", "sql_standard", "iso_8601"]


def main():
    port, n, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    rng = random.Random(seed)
    conn = psycopg.connect(f"host=/tmp port={port} user=postgres dbname=postgres", autocommit=True)
    conn.prepare_threshold = None
    cur = conn.cursor()
    fixed = ["infinity", "-infinity", "0", "-1 mon", "1 mon -1 day", "-1 year +2 mons", "1 day -00:00:01", "-1 day +00:00:01",
             "-0.5 seconds", "00:00:00.000001", "-00:00:00.000001", "1 year -1 mon +1 day -1 hour +1 min -1 sec",
             "178000000 years", "-178000000 years", "2147483647 days", "-2147483648 days", "2147483647 mons",
             "-2147483648 mons", "9223372036 seconds", "-9223372036 seconds", "1 day 2562047788:00:54.775807",
             "-2562047788:00:54.775807", "@ 1 day ago", "P1Y-2M3DT-4H5M-6.5S", "-1 days -00:00:00.5", "0.5 days", "-0.5 mons"]
    vals = list(fixed)
    for _ in range(n):
        mons = rng.choice([0, 0, rng.randint(-30, 30), rng.randint(-2**31, 2**31 - 1)])
        days = rng.choice([0, 0, rng.randint(-40, 40), rng.randint(-2**31, 2**31 - 1)])
        usec = rng.choice([0, rng.randint(-10**11, 10**11), rng.randint(-2**63 + 1, 2**63 - 1), rng.randint(-999999, 999999)])
        vals.append((mons, days, usec))
    bad = 0
    checked = 0
    for v in vals:
        if isinstance(v, tuple):
            mons, days, usec = v
            expr = f"make_interval(months => {mons}) + make_interval(days => {days}) + ({usec} * interval '1 microsecond')"
        else:
            expr = f"interval '{v}'"
        try:
            cur.execute("SET intervalstyle = postgres")
            cur.execute(f"SELECT ({expr})")
        except psycopg.Error:
            continue
        for st in STYLES:
            checked += 1
            try:
                cur.execute(f"SET intervalstyle = {st}")
                cur.execute(f"SELECT ({expr})::text")
                txt = cur.fetchone()[0]
                # reparse under the same style; compare exact fields under postgres style
                cur.execute("SELECT %s::interval::text", (txt,))
                cur.execute("SET intervalstyle = postgres")
                cur.execute(f"""SELECT a.m = b.m AND a.d = b.d AND a.u = b.u, a.*, b.*
                                FROM (SELECT extract(year from x)*12 + extract(month from x) m, extract(day from x) d,
                                             extract(epoch from x) - extract(year from x)*31557600 - extract(month from x)*2592000 - extract(day from x)*86400 u
                                      FROM (SELECT ({expr}) x) s1) a,
                                     (SELECT extract(year from x)*12 + extract(month from x) m, extract(day from x) d,
                                             extract(epoch from x) - extract(year from x)*31557600 - extract(month from x)*2592000 - extract(day from x)*86400 u
                                      FROM (SELECT %s::interval x) s2) b""", (txt,)) if st == "postgres" else None
                cur.execute(f"SET intervalstyle = {st}")
                cur.execute(f"SELECT ({expr})::text = (%s::interval)::text, (%s::interval)::text", (txt, txt))
                same, back = cur.fetchone()
                if not same:
                    bad += 1
                    print(f"ROUNDTRIP DIFF style={st}: value {v!r}\n   out : {txt}\n   back: {back}")
            except psycopg.Error as e:
                bad += 1
                print(f"ROUNDTRIP ERROR style={st}: value {v!r} text={txt!r}: {e.sqlstate} {str(e).splitlines()[0]}")
    print(f"checked={checked} problems={bad}")


if __name__ == "__main__":
    main()
