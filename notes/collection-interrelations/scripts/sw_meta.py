import sys, re, json, html
src, out = sys.argv[1], sys.argv[2]
FEATS = {
  'ksha_sh': re.compile('क्श'),
  'chh': re.compile('च्च्ह'),
  'tilde': re.compile(r'[ऀ-ॿ]~|~[ऀ-ॿ]'),
  'latin_in_deva': re.compile(r'[ऀ-ॿ][A-Za-z]|[A-Za-z][ऀ-ॿ]'),
  'sd_header': re.compile(r'sanskritdocuments|% File name|Encoded by|Proofread by|\.itx|sanskrit@cheerful|cheerful dot', re.I),
}
def feats(t):
    d = {k: len(r.findall(t)) for k, r in FEATS.items()}
    d['deva'] = len(re.findall(r'[ऀ-ॿ]', t))
    return d
def flush(o, page):
    if page and page.get('ns') == '0' and page['revs']:
        r0, rl = page['revs'][0], page['revs'][-1]
        sdmention = any(re.search(r'sanskritdocuments|itx|ITRANS', (r['comment'] or ''), re.I) for r in page['revs'])
        o.write(json.dumps(dict(pageid=page['id'], title=page['title'], nrevs=len(page['revs']),
            first_ts=r0['ts'], first_user=r0['user'], first_comment=(r0['comment'] or '')[:200],
            last_ts=rl['ts'], users=sorted({r['user'] for r in page['revs']})[:20],
            comment_mentions_sd=sdmention, f_first=page['f_first'], f_last=page['f_last'],
            redirect=page.get('redirect', False)), ensure_ascii=False) + '\n')
page = None; inrev = False; rev = None; intext = False; textbuf = []
with open(src, encoding='utf-8') as f, open(out, 'w', encoding='utf-8') as o:
    for line in f:
        s = line.strip()
        if intext:
            textbuf.append(line)
            if '</text>' in line:
                intext = False
                t = html.unescape(''.join(textbuf))
                fe = feats(t)
                if not page['revs'][:-1]: page['f_first'] = fe
                page['f_last'] = fe
            continue
        if s == '<page>':
            flush(o, page); page = dict(revs=[], f_first=None, f_last=None); continue
        if page is None: continue
        if s.startswith('<title>') and 'title' not in page:
            page['title'] = html.unescape(s[7:-8])
        elif s.startswith('<ns>'):
            page['ns'] = s[4:-5]
        elif s.startswith('<id>') and 'id' not in page:
            page['id'] = int(s[4:-5])
        elif s.startswith('<redirect'):
            page['redirect'] = True
        elif s == '<revision>':
            rev = dict(ts=None, user=None, comment=None); page['revs'].append(rev)
        elif rev is not None and s.startswith('<timestamp>'):
            rev['ts'] = s[11:-12]
        elif rev is not None and (s.startswith('<username>') or s.startswith('<ip>')):
            rev['user'] = html.unescape(re.sub(r'</?(username|ip)>', '', s))
        elif rev is not None and s.startswith('<comment>'):
            rev['comment'] = html.unescape(re.sub(r'</?comment>', '', s))
        elif s.startswith('<text') and page.get('ns') == '0':
            if s.endswith('/>'):
                continue
            if '</text>' in s:
                t = html.unescape(s); fe = feats(t)
                if len(page['revs']) == 1: page['f_first'] = fe
                page['f_last'] = fe
            else:
                intext = True; textbuf = [line]
    flush(o, page)
