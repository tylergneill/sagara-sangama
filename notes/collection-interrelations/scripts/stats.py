import json, sys
from collections import Counter
S = sys.argv[1]
sd = [json.loads(l) for l in open(S + '/sd_meta.jsonl')]
print('SD docs in 2020 mirror:', sum(r['in_2020'] for r in sd), '/', len(sd))
ch = [r['sd_changed_since_2020'] for r in sd if r['in_2020']]
print('SD changed since 2020: identical', sum(c == 0 for c in ch), ' <0.2%', sum(0 < c < .002 for c in ch), ' 0.2-2%', sum(.002 <= c < .02 for c in ch), ' >=2%', sum(c >= .02 for c in ch))
R = json.load(open(S + '/pairs_joined.json'))
sdsw = [r for r in R if r['label'].startswith('SD->SW')]
print('SD->SW pairs where SD text changed >=0.2% since 2020:', sum((r['sd_changed_since_2020'] or 0) >= .002 for r in sdsw), 'of', len(sdsw))
new = [r for r in R if r['label'].startswith('SW older; SD later')]
print('SW-older/SD-new: SW first year', Counter(r['sw_first'][:4] for r in new).most_common(20))
print('  SD credited to:', Counter(r['sd_by'] for r in new).most_common(12))
print('  SD folder:', Counter(r['sd'].split('/')[0] for r in new).most_common(10))
print('  SW first users:', Counter(r['sw_first_users'][0] for r in new).most_common(8))
print('  with SW converter artefacts:', sum(r['itrans_artefacts_per_10k'] >= 5 for r in new))
