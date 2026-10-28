import json, sys, re
from datetime import datetime
from collections import Counter
S = sys.argv[1]
sw = {}
for l in open(S + '/sw_meta.jsonl', encoding='utf-8'):
    r = json.loads(l); sw[r['pageid']] = r
sd = {}
for l in open(S + '/sd_meta.jsonl', encoding='utf-8'):
    r = json.loads(l); sd[r['doc']] = r
def pdate(s):
    if not s: return None
    s = re.sub(r'\s+', ' ', s.strip().rstrip('.'))
    for fmt in ('%B %d, %Y', '%B %d %Y', '%b %d, %Y', '%d %B %Y', '%B, %d, %Y', '%B %Y', '%Y'):
        try: return datetime.strptime(s, fmt).date().isoformat()
        except ValueError: pass
    m = re.search(r'(19|20)\d\d', s)
    return m.group(0) + '-06-30' if m else None
rows = []
for l in open(S + '/pairs.jsonl', encoding='utf-8'):
    p = json.loads(l)
    if max(p['cont_sd'], p['cont_sw']) < 0.5: continue
    metas = [sw[i] for i in p['sw_pages'] if i in sw]
    if not metas: continue
    first = min(m['first_ts'] for m in metas)[:10]
    users = Counter(m['first_user'] for m in metas).most_common(2)
    fp = Counter()
    for m in metas:
        for k, v in (m['f_first'] or {}).items(): fp[k] += v
    deva = fp.pop('deva', 0) or 1
    artefacts = fp['ksha_sh'] + fp['chh'] + fp['tilde'] + fp['latin_in_deva']
    d = sd[p['sd']]
    sd_now, sd_20 = pdate(d.get('update')), pdate(d.get('update_2020'))
    if d.get('wikisource_credit'): lab = 'SW->SD (SD credits Wikisource)'
    elif d.get('in_2020') and sd_20 and sd_20 < first: lab = 'SD->SW (SD older)'
    elif not d.get('in_2020') and sd_now and first < sd_now: lab = 'SW older; SD later (SW->SD possible)'
    elif d.get('in_2020') and sd_20 and sd_20 >= first: lab = 'SW older than SD-2020 update (unclear)'
    else: lab = 'unclear'
    if fp['sd_header']: lab += ' +SD header in SW'
    stale = d.get('in_2020') and (d.get('sd_changed_since_2020') or 0) > 0 and lab.startswith('SD->SW')
    rows.append(dict(label=lab, stale_fork=bool(stale), sd=p['sd'], sd_title=d.get('title'), sw=p['sw'], sw_npages=p['sw_npages'],
        cont_sd=p['cont_sd'], cont_sw=p['cont_sw'], sw_first=first, sw_first_users=[u for u, _ in users],
        sd_update=sd_now, sd_in_2020=d.get('in_2020'), sd_update_2020=sd_20, sd_changed_since_2020=d.get('sd_changed_since_2020'),
        sd_by=d.get('translit_by') or d.get('proof_by'), itrans_artefacts_per_10k=round(artefacts / deva * 1e4, 2), sd_header_in_sw=fp['sd_header']))
json.dump(rows, open(S + '/pairs_joined.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(rows), 'pairs with containment>=0.5')
print(Counter(r['label'] for r in rows).most_common())
print('stale forks (SD->SW and SD text changed since 2020):', sum(r['stale_fork'] for r in rows))
hi = [r for r in rows if r['itrans_artefacts_per_10k'] >= 5]
print('pairs whose SW first rev has ITRANS-converter artefacts >=5/10k chars:', len(hi), Counter(r['label'].split(' (')[0] for r in hi).most_common())
print('top SW first-uploaders in SD->SW:', Counter(u for r in rows if r['label'].startswith('SD->SW') for u in r['sw_first_users'][:1]).most_common(8))
print('top SW first-uploaders in SW-older:', Counter(u for r in rows if r['label'].startswith('SW older') for u in r['sw_first_users'][:1]).most_common(8))
