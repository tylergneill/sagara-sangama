import sys, difflib
sys.path.insert(0, sys.argv[1])
from textsrc import *
S = sys.argv[1]
D = '/Users/tyler/Git/sagara-sangama/third_party_dumps/sanskrit-documents'
sd00 = sd_html(D + '/2020-sanskrit-documents-dump/sanskritdocuments.org/doc_upanishhat/jabaladarshana.html')
sd21 = sd_html('/Users/tyler/Git/sagara-sangama/atlases/sanskrit-documents-atlas/data/fulltext_cache/doc_upanishhat/jabaladarshana.html')
revs = hist_revs(S + '/hist.xml')
titles = [f'जाबालदर्शनोपनिषत्/खण्डः {n}' for n in '१ २ ३ ४ ५ ६ ७ ८ ९ १०'.split()]
sw12 = '\n'.join(revs[t][0][1] for t in titles)
swnow = '\n'.join(revs[t][-1][1] for t in titles)
T = {k: toks(v) for k, v in dict(sd00=sd00, sd21=sd21, sw12=sw12, swnow=swnow).items()}
def align(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    m = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size): m[blk.a + k] = blk.b + k
    return sm, m
for x, y in [('sd00','sw12'),('sw12','swnow'),('sd00','sd21'),('swnow','sd21'),('sd00','swnow')]:
    sm = difflib.SequenceMatcher(None, T[x], T[y], autojunk=False)
    nd = sum(1 for o in sm.get_opcodes() if o[0] != 'equal')
    print(f'{x:6} vs {y:6}: diff-hunks={nd:4}  ratio={sm.ratio():.4f}')
print()
# classify swnow vs sd21 hunks by what sd00 had
base = T['sd00']
_, m_sw = align(T['swnow'], base); _, m_sd = align(T['sd21'], base)
sm = difflib.SequenceMatcher(None, T['swnow'], T['sd21'], autojunk=False)
from collections import Counter
cls = Counter()
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == 'equal': continue
    sw_seg = T['swnow'][i1:i2]; sd_seg = T['sd21'][j1:j2]
    # locate base region via anchors
    a0 = m_sw.get(i1-1, None); a1 = m_sw.get(i2, None)
    b_seg = base[a0+1:a1] if a0 is not None and a1 is not None else None
    if b_seg is None: c = 'unanchored'
    elif b_seg == sw_seg and b_seg != sd_seg: c = 'SD-revised-since-2000 (SW=old SD)'
    elif b_seg == sd_seg and b_seg != sw_seg: c = 'SW-changed (SD=old SD)'
    else: c = 'both-differ-from-old-SD'
    cls[c] += 1
    print(f'{c:38} SW:{" ".join(sw_seg)[:60]:30} SD21:{" ".join(sd_seg)[:60]:30} SD00:{" ".join(b_seg or [])[:60]}')
print(cls)
