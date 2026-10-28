import sys, re, difflib
sys.path.insert(0, sys.argv[1])
from iastnorm import ortho
from collections import Counter
def toks(path):
    t = open(path, encoding='utf-8').read()
    t = re.sub(r'<[^>]*>', ' ', t)
    t = re.sub(r"[।॥|\d\.\-—,;:?!()\[\]\"“”*_=#/]", ' ', t)
    t = re.sub(r'(?<=\s)p(?=\s)', ' ', t)
    return t.split()
a, b = toks(sys.argv[2]), toks(sys.argv[3])
sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
c = Counter(); subst = []
for op,i1,i2,j1,j2 in sm.get_opcodes():
    if op == 'equal': continue
    A, B = ' '.join(a[i1:i2]), ' '.join(b[j1:j2])
    if ortho(A) == ortho(B): c['orthographic (nasal/space/avagraha/m-final)'] += 1
    elif not A or not B: c['insert/delete'] += 1; subst.append((op, ' '.join(a[max(0,i1-3):i1]), A, B))
    else: c['substantive'] += 1; subst.append((op, ' '.join(a[max(0,i1-3):i1]), A, B))
print(c)
for s in subst: print(f'{s[0]:7} [{s[1][-40:]}]  SW: {s[2][:110]}  ||  SD: {s[3][:110]}')
