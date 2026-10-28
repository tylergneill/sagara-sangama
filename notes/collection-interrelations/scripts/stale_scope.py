import json, sys
S = sys.argv[1]
R = json.load(open(S + '/pairs_joined.json'))
pairs = {(json.loads(l)['sw'], json.loads(l)['sd']): json.loads(l)['sw_pages'] for l in open(S + '/pairs.jsonl')}
scope = [r for r in R if r['sd_in_2020'] and (r['sd_changed_since_2020'] or 0) >= 0.002]
pages = set()
for r in scope:
    r['sw_pages'] = pairs[(r['sw'], r['sd'])]; pages.update(r['sw_pages'])
json.dump(scope, open(S + '/stale_scope.json', 'w'), ensure_ascii=False)
open(S + '/stale_pages.txt', 'w').write(','.join(map(str, sorted(pages))))
from collections import Counter
print(len(scope), 'pairs;', len({r['sd'] for r in scope}), 'SD docs;', len(pages), 'SW pages', Counter(r['label'].split(' (')[0] for r in scope))
