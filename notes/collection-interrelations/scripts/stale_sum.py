import json, sys
from collections import Counter, defaultdict
S = sys.argv[1]
R = json.load(open(S + '/stale_results.json'))
for r in R:
    if r['sd'].endswith('jabaladarshana'): print('CHECK', {k: v for k, v in r.items() if k not in ('label',)})
print(Counter(r['status'] for r in R))
ok = [r for r in R if r['status'] == 'ok' and r.get('sites', 0) > 0]
# per SD doc keep the SW group that best contains it
best = {}
for r in ok:
    if r['sd'] not in best or r['cont_sd'] > best[r['sd']]['cont_sd']: best[r['sd']] = r
B = list(best.values())
def agg(rows, title):
    t = Counter()
    for r in rows:
        for k, v in r.items():
            if k.startswith(('now_', 'first_')) or k in ('sites', 'big'): t[k] += v
    loc = t['now_old'] + t['now_new'] + t['now_both']
    print(f"\n== {title}: {len(rows)} SD docs, {t['sites']} substantive SD change sites (+{t['big']} large rewrites skipped)")
    print(f"  SW now:   old(stale)={t['now_old']}  new(has SD fix)={t['now_new']}  both={t['now_both']}  not found={t['now_neither']}  -> stale share of located: {t['now_old']/max(loc,1):.1%}")
    print(f"  SW first: old={t['first_old']}  new={t['first_new']}  both={t['first_both']}  not found={t['first_neither']}")
    docs_stale = sum(1 for r in rows if r.get('now_old', 0) > 0)
    docs_upd = sum(1 for r in rows if r.get('now_new', 0) > 0)
    docs_clean_stale = sum(1 for r in rows if r.get('now_old', 0) > 0 and r.get('now_new', 0) == 0)
    print(f"  docs where SW keeps >=1 pre-fix SD reading: {docs_stale}; only pre-fix (never updated): {docs_clean_stale}; docs where SW has >=1 SD fix: {docs_upd}")
agg(B, 'ALL (best SW match per SD doc)')
agg([r for r in B if r['label'].startswith('SD->SW')], 'SD->SW by dates')
agg([r for r in B if not r['label'].startswith('SD->SW')], 'other labels')
json.dump(B, open(S + '/stale_best.json', 'w'), ensure_ascii=False)
