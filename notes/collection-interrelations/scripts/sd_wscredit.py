import os, re, html
from collections import Counter
root = '/Users/tyler/Git/sagara-sangama/atlases/sanskrit-documents-atlas/data/fulltext_cache'
c = Counter(); n = 0
for dp, _, fs in os.walk(root):
    for f in fs:
        t = open(os.path.join(dp, f), encoding='utf-8', errors='replace').read()
        if 'wikisource' not in t.lower(): continue
        n += 1
        inf = re.search(r'<pre class="inf">(.*?)</pre>', t, re.S)
        where = 'inf' if inf and 'wikisource' in inf.group(1).lower() else 'body/other'
        for m in re.finditer(r'[^\n]{0,50}wikisource[^\n]{0,40}', t, re.I):
            c[(where, re.sub(r'<[^>]+>', '', html.unescape(m.group(0))).strip()[:110])] += 1
print(n)
for k, v in c.most_common(30): print(v, k)
