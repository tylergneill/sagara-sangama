import os, re, html, json, sys, difflib, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textsrc import sd_html, toks
CUR = '/Users/tyler/Git/sagara-sangama/atlases/sanskrit-documents-atlas/data/fulltext_cache'
OLD = '/Users/tyler/Git/sagara-sangama/third_party_dumps/sanskrit-documents/2020-sanskrit-documents-dump/sanskritdocuments.org'
old_by_name = {}
for dp, _, fs in os.walk(OLD):
    for f in fs:
        if f.endswith('.html'): old_by_name.setdefault(f, []).append(os.path.join(dp, f))
def inf(path):
    t = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r'<pre class="inf">(.*?)</pre>', t, re.S)
    d = {}
    if m:
        for line in html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).splitlines():
            mm = re.match(r'%\s*([^:]+?)\s*:\s*(.*)', line)
            if mm: d[mm.group(1).strip()] = mm.group(2).strip()
    else:
        mm = re.search(r'Latest update\s*:\s*([^\n<]*)', t)
        if mm: d['Latest update'] = mm.group(1).strip()
    return d
out = open(sys.argv[1], 'w', encoding='utf-8')
for dp, _, fs in os.walk(CUR):
    for f in sorted(fs):
        if not f.endswith('.html'): continue
        p = os.path.join(dp, f); rel = os.path.relpath(p, CUR)
        d = inf(p)
        rec = dict(doc=rel[:-5], title=d.get('Text title'), itx=d.get('itxtitle'), update=d.get('Latest update'),
                   translit_by=d.get('Transliterated by'), proof_by=d.get('Proofread by'),
                   wikisource_credit=('wikisource' in json.dumps(d).lower()))
        op = os.path.join(OLD, rel)
        if not os.path.exists(op):
            c = old_by_name.get(f, []); op = c[0] if len(c) == 1 else None
        if op:
            d0 = inf(op); rec['in_2020'] = True; rec['update_2020'] = d0.get('Latest update')
            a, b = toks(sd_html(op)), toks(sd_html(p))
            if a == b: rec['sd_changed_since_2020'] = 0.0
            elif len(a) + len(b) < 120000:
                sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
                rec['sd_changed_since_2020'] = round(1 - sm.ratio(), 4)
            else:
                rec['sd_changed_since_2020'] = round(1 - difflib.SequenceMatcher(None, a, b).quick_ratio(), 4)
        else:
            rec['in_2020'] = False
        out.write(json.dumps(rec, ensure_ascii=False) + '\n')
