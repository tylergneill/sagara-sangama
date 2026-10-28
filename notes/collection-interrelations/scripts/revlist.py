import sys, re
t = open(sys.argv[1], encoding='utf-8').read()
for page in re.findall(r'<title>.*?</page>', t, re.S):
    title = re.search(r'^(.*?)</title>', page).group(1)
    print('==', title)
    for rev in re.findall(r'<revision>(.*?)</revision>', page, re.S):
        ts = re.search(r'<timestamp>(.*?)</timestamp>', rev).group(1)
        user = re.search(r'<username>(.*?)</username>|<ip>(.*?)</ip>', rev)
        cm = re.search(r'<comment>(.*?)</comment>', rev, re.S)
        txt = re.search(r'<text[^>]*>(.*?)</text>', rev, re.S)
        n = len(txt.group(1)) if txt else 0
        print(' ', ts, (user.group(1) or user.group(2)) if user else '?', n, (cm.group(1)[:80] if cm else ''))
