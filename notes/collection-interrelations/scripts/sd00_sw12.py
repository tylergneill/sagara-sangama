import sys, difflib
sys.path.insert(0, sys.argv[1])
from textsrc import *
D = '/Users/tyler/Git/sagara-sangama/third_party_dumps/sanskrit-documents'
a = toks(sd_html(D + '/2020-sanskrit-documents-dump/sanskritdocuments.org/doc_upanishhat/jabaladarshana.html'))
revs = hist_revs(sys.argv[1] + '/hist.xml')
titles = [f'जाबालदर्शनोपनिषत्/खण्डः {n}' for n in '१ २ ३ ४ ५ ६ ७ ८ ९ १०'.split()]
for idx, lab in [(0,'sw2012'),(1,'sw-rev2')]:
    b = toks('\n'.join(revs[t][min(idx,len(revs[t])-1)][1] for t in titles))
    print('=====', lab)
    for op,i1,i2,j1,j2 in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
        if op!='equal': print(' ', op, ' '.join(a[i1:i2])[:70], '->', ' '.join(b[j1:j2])[:70])
