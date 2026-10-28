import json, sys, os, re, difflib, random
sys.path.insert(0, sys.argv[1]); S = sys.argv[1]
from iastnorm import ortho
SD = '/Users/tyler/Git/sagara-sangama/atlases/sanskrit-documents-atlas/data/text_extract/'
SWX = '/Users/tyler/Git/sagara-sangama/atlases/sanskrit-wikisource-atlas/data/text_extract/'
idx = {}
for l in open(SWX + 'index.jsonl', encoding='utf-8'):
    r = json.loads(l); idx[r['pageid']] = r['path']
pairs = {(json.loads(l)['sw'], json.loads(l)['sd']): json.loads(l)['sw_pages'] for l in open(S + '/pairs.jsonl', encoding='utf-8')}
def tk(t):
    t = re.sub(r"[।॥|\d\.\-—,;:?!()\[\]\"“”*_=#/]", ' ', t)
    return [w for w in (ortho(x) for x in t.split()) if w]
R = json.load(open(S + '/pairs_joined.json'))
sel = [r for r in R if r['label'].startswith(sys.argv[2]) and r['cont_sd'] >= 0.6]
random.seed(7); sel = random.sample(sel, min(int(sys.argv[3]), len(sel)))
tot = dict(tok=0, hunks=0); show = []
for r in sel:
    sdt = tk(open(SD + r['sd'] + '.txt', encoding='utf-8').read())
    best = None; bs = set(sdt)
    for pid in pairs[(r['sw'], r['sd'])]:
        p = SWX + 'iast/' + idx.get(pid, '')
        if not os.path.isfile(p): continue
        w = tk(open(p, encoding='utf-8').read()); sc = len(bs & set(w))
        if not best or sc > best[0]: best = (sc, w)
    if not best: continue
    sw = best[1]
    sm = difflib.SequenceMatcher(None, sdt, sw, autojunk=False)
    mb = [b for b in sm.get_matching_blocks() if b.size >= 3]
    if not mb: continue
    lo, hi = mb[0].b, mb[-1].b + mb[-1].size
    sm = difflib.SequenceMatcher(None, sdt, sw[lo:hi], autojunk=False)
    h = [(sdt[i1:i2], sw[lo+j1:lo+j2]) for op,i1,i2,j1,j2 in sm.get_opcodes() if op == 'replace' and ''.join(sdt[i1:i2]) != ''.join(sw[lo+j1:lo+j2])]
    tot['tok'] += len(sdt); tot['hunks'] += len(h)
    show.append((r['sd'], len(sdt), len(h), h[:6]))
print(sys.argv[2], 'pairs', len(show), 'substantive replace-hunks per 1000 SD tokens:', round(1000 * tot['hunks'] / max(tot['tok'], 1), 1))
for s in show[:5]:
    print(' ', s[0], s[1], 'tok', s[2], 'hunks')
    for a, b in s[3]: print('     SD:', ' '.join(a)[:50], '| SW:', ' '.join(b)[:50])
