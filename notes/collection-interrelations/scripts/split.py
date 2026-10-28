import json, sys
B = [r for r in json.load(open(sys.argv[1] + '/stale_best.json')) if not r['sd'].endswith('/artha')]
for lab, sel in (('SW created before 2020-06-27 mirror', lambda r: r['sw_first'] < '2020-06-27'), ('SW created after', lambda r: r['sw_first'] >= '2020-06-27')):
    R = [r for r in B if sel(r)]
    g = lambda k: sum(r.get(k, 0) for r in R)
    print(f"{lab}: {len(R)} docs | at creation old={g('first_old')} new={g('first_new')} | now old={g('now_old')} new={g('now_new')} | fixes gained after creation={g('now_new')-g('first_new')}")
