import sys, difflib, re
sys.path.insert(0, sys.argv[1])
from textsrc import *
from skrutable.transliteration import Transliterator
tr = Transliterator()
iast = lambda s: tr.transliterate(s, from_scheme='DEV', to_scheme='IAST')
W = '/Users/tyler/Library/CloudStorage/Dropbox/Docs/Projects/Computational/muktabodha/HYP/txt/1_parallel_etexts/15/'
D = '/Users/tyler/Git/sagara-sangama/third_party_dumps/sanskrit-documents'
ebs = toks(clean(open(W + 'EBS_mula_1-9.txt', encoding='utf-8').read()).replace('m̐', '~'))
revs = hist_revs(sys.argv[1] + '/hist.xml')
titles = [f'जाबालदर्शनोपनिषत्/खण्डः {n}' for n in '१ २ ३ ४ ५ ६ ७ ८ ९'.split()]
cands = {
  'sd2000': sd_html(D + '/2020-sanskrit-documents-dump/sanskritdocuments.org/doc_upanishhat/jabaladarshana.html'),
  'sd2021': sd_html('/Users/tyler/Git/sagara-sangama/atlases/sanskrit-documents-atlas/data/fulltext_cache/doc_upanishhat/jabaladarshana.html'),
  'sw2012': '\n'.join(revs[t][0][1] for t in titles),
  'sw2019': '\n'.join(revs[t][1][1] for t in titles),
  'swnow': '\n'.join(revs[t][-1][1] for t in titles),
}
for k, v in cands.items():
    b = toks(iast(v).replace('~', ' ~ '))
    sm = difflib.SequenceMatcher(None, ebs, b, autojunk=False)
    hunks = [o for o in sm.get_opcodes() if o[0] != 'equal']
    print(f'EBS vs {k:7}: hunks={len(hunks):4}  ratio={sm.ratio():.4f}')
    if k in ('sw2012',):
        for op,i1,i2,j1,j2 in hunks[:40]: print('    ', op, ' '.join(ebs[i1:i2])[:60], '|', ' '.join(b[j1:j2])[:60])
