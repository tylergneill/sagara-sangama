import sys, re, json, html
src, out, ids = sys.argv[1], sys.argv[2], set(map(int, open(sys.argv[3]).read().split(',')))
o = open(out, 'w', encoding='utf-8')
pid = None; keep = False; intext = False; buf = []; revs = []; ts = None
for line in open(src, encoding='utf-8'):
    s = line.strip()
    if intext:
        buf.append(line)
        if '</text>' in line:
            intext = False; revs.append((ts, html.unescape(re.sub(r'^\s*<text[^>]*>|</text>\s*$', '', ''.join(buf)))))
        continue
    if s == '<page>':
        pid = None; keep = False; revs = []; continue
    if pid is None and s.startswith('<id>'):
        pid = int(s[4:-5]); keep = pid in ids; continue
    if not keep: continue
    if s.startswith('<timestamp>'): ts = s[11:-12]
    elif s.startswith('<text'):
        if s.endswith('/>'): revs.append((ts, ''))
        elif '</text>' in s: revs.append((ts, html.unescape(re.sub(r'^\s*<text[^>]*>|</text>\s*$', '', s))))
        else: intext = True; buf = [line]
    elif s == '</page>' and revs:
        o.write(json.dumps(dict(pageid=pid, n=len(revs), first_ts=revs[0][0], last_ts=revs[-1][0], first=revs[0][1], last=revs[-1][1]), ensure_ascii=False) + '\n')
