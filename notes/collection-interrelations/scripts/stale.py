import sys, os, json, re, difflib, unicodedata
from multiprocessing import Pool
S = sys.argv[1]; sys.path.insert(0, S)
from textsrc import sd_html, wikitext, toks
CUR = '/Users/tyler/Git/sagara-sangama/atlases/sanskrit-documents-atlas/data/fulltext_cache/'
OLD = '/Users/tyler/Git/sagara-sangama/third_party_dumps/sanskrit-documents/2020-sanskrit-documents-dump/sanskritdocuments.org/'
def norm(s):
    s = unicodedata.normalize('NFC', s).replace('‍', '').replace('‌', '')
    s = s.replace('क्श', 'क्ष').replace('च्च्ह', 'छ').replace('~', '').replace('ऽ', '')
    s = re.sub(r'[ङञणनम]्(?=[क-ह])', 'ं', s)
    s = re.sub(r'म्(?=[\s।॥|0-9०-९]|$)', 'ं', s)
    return re.sub(r'[^ऀ-ॣ॰-ॿ]', '', s)
def old_path(doc):
    p = OLD + doc + '.html'
    if os.path.exists(p): return p
    name = os.path.basename(doc) + '.html'
    for dp, _, fs in os.walk(OLD):
        if name in fs: return os.path.join(dp, name)
def sites(doc):
    op = old_path(doc)
    if not op: return doc, None
    a, b = toks(sd_html(op)), toks(sd_html(CUR + doc + '.html'))
    if len(a) + len(b) > 200000: return doc, 'too_big'
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal': continue
        o, n = norm(' '.join(a[i1:i2])), norm(' '.join(b[j1:j2]))
        if o == n: continue
        L, R = norm(' '.join(a[max(0, i1 - 5):i1]))[-10:], norm(' '.join(a[i2:i2 + 5]))[:10]
        if len(L) < 6 or len(R) < 6: continue
        if len(o) > 150 or len(n) > 150: out.append(('big', L, o[:60], n[:60], R)); continue
        out.append(('site', L, o, n, R))
    return doc, out
if __name__ == '__main__':
    scope = json.load(open(S + '/stale_scope.json'))
    docs = sorted({r['sd'] for r in scope})
    with Pool(max(2, os.cpu_count() - 1)) as p:
        SITES = dict(p.map(sites, docs, chunksize=4))
    json.dump(SITES, open(S + '/sd_sites.json', 'w'), ensure_ascii=False)
    need = set(); [need.update(r['sw_pages']) for r in scope]
    SW = {}
    for l in open(S + '/sw_fl.jsonl', encoding='utf-8'):
        d = json.loads(l)
        if d['pageid'] in need: SW[d['pageid']] = (norm(wikitext(d['first'])), norm(wikitext(d['last'])), d['first_ts'], d['last_ts'])
    rows = []
    for r in scope:
        st = SITES.get(r['sd'])
        res = dict(sd=r['sd'], sw=r['sw'], label=r['label'], cont_sd=r['cont_sd'], sw_first=r['sw_first'], sd_update_2020=r['sd_update_2020'], sd_update=r['sd_update'], status='ok')
        if not isinstance(st, list): res['status'] = st or 'no_2020'; rows.append(res); continue
        pg = [SW[i] for i in r['sw_pages'] if i in SW]
        first = '|'.join(x[0] for x in pg); last = '|'.join(x[1] for x in pg)
        c = dict(sites=0, big=0)
        ex = []
        for kind, L, o, n, R in st:
            if kind == 'big': c['big'] += 1; continue
            c['sites'] += 1
            po, pn = L + o + R, L + n + R
            for lab, txt in (('now', last), ('first', first)):
                ho, hn = po in txt, pn in txt
                k = f'{lab}_' + ('both' if ho and hn else 'old' if ho else 'new' if hn else 'neither')
                c[k] = c.get(k, 0) + 1
            if po in last and pn not in last and len(ex) < 4: ex.append((o, n))
        res.update(c); res['stale_examples'] = ex; rows.append(res)
    json.dump(rows, open(S + '/stale_results.json', 'w'), ensure_ascii=False, indent=0)
    print('done', len(rows))
