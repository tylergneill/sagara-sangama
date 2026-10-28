import sys, re
src, out = sys.argv[1], sys.argv[2]
targets = set(sys.argv[3].split(','))
buf = []; inpage = False; pid = None; keep = False
with open(src, encoding='utf-8') as f, open(out, 'w', encoding='utf-8') as o:
    for line in f:
        if '<page>' in line:
            inpage = True; buf = [line]; pid = None; keep = False; continue
        if inpage:
            if pid is None:
                m = re.match(r'\s*<id>(\d+)</id>', line)
                if m:
                    pid = m.group(1); keep = pid in targets
                buf.append(line)
            elif keep:
                o.write(''.join(buf)) if buf else None; buf = []
                o.write(line)
            if '</page>' in line:
                inpage = False; buf = []
