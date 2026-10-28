import json, sys, random
from collections import Counter
S = sys.argv[1]
B = json.load(open(S + '/stale_best.json'))
B.sort(key=lambda r: -r.get('now_old', 0))
tot = sum(r.get('now_old', 0) for r in B)
print('top docs by stale sites (share of all stale):')
cum = 0
for r in B[:12]:
    cum += r.get('now_old', 0)
    print(f"  {r.get('now_old',0):4} old / {r.get('now_new',0):3} new / {r['sites']:4} sites  {r['sd'][:50]:50} SW:{r['sw'][:28]}  first {r['sw_first']}  SD {r['sd_update_2020']}->{r['sd_update']}")
print(f'top12 = {cum/tot:.0%} of stale sites')
med = sorted(r.get('now_old', 0) for r in B if r.get('now_old', 0)); print('median stale sites per affected doc:', med[len(med)//2])
random.seed(3)
ex = [(r['sd'], e) for r in B for e in r['stale_examples']]
print('\nrandom stale examples (SD-2020 reading still in SW  ->  SD now):')
for d, (o, n) in random.sample(ex, 30): print(f'  {o[:40]:>40}  ->  {n[:40]:40}  [{d.split("/")[-1][:30]}]')
