import sys, re, difflib
sys.path.insert(0, sys.argv[1])
from iastnorm import ortho
from collections import Counter
exec(open(sys.argv[1] + '/classify.py').read().split('a, b = toks')[0].split('from collections import Counter')[1])
W = sys.argv[2]
a, b = toks(W + 'SW1_all.txt'), toks(W + 'SD_all.txt')
mula = ''.join(ortho(t) for t in toks(W + 'SD1_mula.txt') + toks(W + 'SW2_mula.txt'))
sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
c = Counter(); rows = []
for op,i1,i2,j1,j2 in sm.get_opcodes():
    if op != 'replace': continue
    A, B = ' '.join(a[i1:i2]), ' '.join(b[j1:j2])
    oa, ob = ortho(A), ortho(B)
    if oa == ob: continue
    # use 2-token context so the mula check is about the passage, not a common word
    ctxA = ortho(' '.join(a[max(0,i1-1):i2+1])); ctxB = ortho(' '.join(b[max(0,j1-1):j2+1]))
    ina, inb = ctxA in mula, ctxB in mula
    v = 'SW=mula' if ina and not inb else 'SD=mula' if inb and not ina else 'both' if ina else 'neither (commentary or both off)'
    c[v] += 1; rows.append((v, A, B))
print(c)
for v, A, B in rows:
    if v in ('SW=mula', 'SD=mula'): print(f'{v:8} SW: {A[:70]:45} SD: {B[:70]}')
