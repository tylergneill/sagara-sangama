import os, sys, json, re, unicodedata
import numpy as np
from collections import defaultdict
SD = '/Users/tyler/Git/sagara-sangama/atlases/sanskrit-documents-atlas/data/text_extract'
SWX = '/Users/tyler/Git/sagara-sangama/atlases/sanskrit-wikisource-atlas/data/text_extract'
K, MOD = 16, 16
P = np.uint64(1099511628211)
def norm(s):
    s = unicodedata.normalize('NFC', s).lower()
    s = s.replace('kś', 'kṣ').replace('ḻ', 'l').replace('m̐', 'ṃ')
    s = re.sub(r'ṅ(?=\s*[kg])|ñ(?=\s*[cj])|ṇ(?=\s*[ṭḍ])|n(?=\s*[td])|m(?=\s*[pb])', 'ṃ', s)
    s = re.sub(r'm(?=\s|$)', 'ṃ', s)
    return re.sub(r'[^a-zāīūṛṝḷḹṃḥṅñṭḍṇśṣ]', '', s)
def shingles(s):
    if len(s) < K: return np.empty(0, np.uint64), 0
    a = np.frombuffer(s.encode('utf-32-le'), dtype=np.uint32).astype(np.uint64)
    n = len(a) - K + 1
    h = np.zeros(n, np.uint64)
    with np.errstate(over='ignore'):
        for i in range(K):
            h = h * P + a[i:i + n] * np.uint64(2654435761)
        h ^= h >> np.uint64(29)
        h *= np.uint64(0xbf58476d1ce4e5b9)
        h ^= h >> np.uint64(32)
    h = h[(h % np.uint64(MOD)) == 0]
    return np.unique(h), len(s)
# --- SD index
sd_docs, sd_len, H, D = [], [], [], []
for dp, _, fs in os.walk(SD):
    for f in sorted(fs):
        if not f.endswith('.txt'): continue
        rel = os.path.relpath(os.path.join(dp, f), SD)[:-4]
        h, L = shingles(norm(open(os.path.join(dp, f), encoding='utf-8').read()))
        if len(h) == 0: continue
        i = len(sd_docs); sd_docs.append(rel); sd_len.append(len(h))
        H.append(h); D.append(np.full(len(h), i, np.int32))
H = np.concatenate(H); D = np.concatenate(D)
o = np.argsort(H, kind='stable'); H, D = H[o], D[o]
uh, start, cnt = np.unique(H, return_index=True, return_counts=True)
print('SD docs', len(sd_docs), 'shingles', len(H), 'unique', len(uh), file=sys.stderr)
DFMAX = 8
# --- SW groups
groups = defaultdict(list)
for line in open(os.path.join(SWX, 'index.jsonl'), encoding='utf-8'):
    r = json.loads(line)
    if r['ns'] != 'main': continue
    groups[r['title'].split('/')[0].strip()].append(r)
out = open(sys.argv[1], 'w', encoding='utf-8')
ng = 0
for g, rs in groups.items():
    text = []
    for r in rs:
        p = os.path.join(SWX, 'iast', r['path'])
        if os.path.exists(p): text.append(open(p, encoding='utf-8').read())
    h, L = shingles(norm('\n'.join(text)))
    if len(h) < 5: continue
    _, hit, _ = np.intersect1d(uh, h, assume_unique=True, return_indices=True)
    hit = hit[cnt[hit] <= DFMAX]
    if len(hit) == 0: continue
    docs = np.concatenate([D[start[j]:start[j] + cnt[j]] for j in hit])
    bc = np.bincount(docs, minlength=len(sd_docs))
    for di in np.nonzero(bc >= 8)[0]:
        sh = int(bc[di]); csd = sh / sd_len[di]; csw = sh / len(h)
        if max(csd, csw) >= 0.15:
            out.write(json.dumps(dict(sw=g, sw_pages=[r['pageid'] for r in rs][:400], sw_npages=len(rs), sd=sd_docs[di],
                shared=sh, sd_sh=sd_len[di], sw_sh=len(h), cont_sd=round(csd, 4), cont_sw=round(csw, 4)), ensure_ascii=False) + '\n')
    ng += 1
    if ng % 2000 == 0: print('groups', ng, file=sys.stderr); out.flush()
print('done groups', ng, file=sys.stderr)
