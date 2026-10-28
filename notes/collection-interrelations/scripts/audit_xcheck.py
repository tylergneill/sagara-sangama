import sys, re, html, json
from types import SimpleNamespace
sys.path.insert(0, '/Users/tyler/Git/sagara-sangama/atlases/sanskrit-wikisource-atlas')
from pipeline.audit import find_bulk_import_candidates
S = sys.argv[1]
recs = []; title = ns = None; intext = False; buf = []
for line in open(sys.argv[2], encoding='utf-8'):
    s = line.strip()
    if intext:
        buf.append(line)
        if '</text>' in line: intext = False; recs.append(SimpleNamespace(title=title, text=html.unescape(''.join(buf))))
        continue
    if s.startswith('<title>'): title = html.unescape(s[7:-8])
    elif s.startswith('<ns>'): ns = s[4:-5]
    elif s.startswith('<text') and ns == '0' and not s.endswith('/>'):
        if '</text>' in s: recs.append(SimpleNamespace(title=title, text=html.unescape(s)))
        else: intext = True; buf = [line]
cand = find_bulk_import_candidates(recs)
sdlinked = {t for t, d in cand.items() if 'sanskritdocuments.org' in d}
anylink = {r.title for r in recs if 'sanskritdocuments' in r.text}
print('audit sanskritdocuments candidates:', len(sdlinked), '| pages mentioning sanskritdocuments at all:', len(anylink))
R = json.load(open(S + '/pairs_joined.json'))
pairs = [json.loads(l) for l in open(S + '/pairs.jsonl')]
mine_groups = {r['sw'] for r in R if r['label'].startswith('SD->SW')}
top = lambda t: t.split('/')[0].strip()
aud_groups = {top(t) for t in sdlinked}
any_groups = {top(t) for t in anylink}
allmatched = {p['sw'] for p in pairs}
print('SW texts: content-matched SD->SW =', len(mine_groups), '| audit-flagged =', len(aud_groups))
print('  flagged by audit AND content-matched SD->SW:', len(aud_groups & mine_groups))
print('  flagged by audit, content-matched any SD doc (any label/threshold):', len(aud_groups & allmatched))
print('  flagged by audit, no content match:', len(aud_groups - allmatched), sorted(aud_groups - allmatched)[:12])
print('  content-matched SD->SW but no sanskritdocuments mention anywhere:', len(mine_groups - any_groups))
st = json.load(open(S + '/stale_best.json'))
stale_groups = {r['sw'] for r in st if r.get('now_old', 0) > 0}
print('  stale SW texts (staleness test) carrying any SD attribution:', len(stale_groups & any_groups), 'of', len(stale_groups))
