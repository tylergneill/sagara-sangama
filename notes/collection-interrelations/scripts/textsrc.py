import re, html, unicodedata
PUNCT = r"[।॥|\d०-९\.\-—,;:?!()\[\]\"“”*_=/←~{}<>#'&]"
def clean(t):
    t = unicodedata.normalize('NFC', t).replace('‍', '').replace('‌', '')
    return t
def sd_html(path):
    t = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r'<pre[^>]*id="content"[^>]*>(.*?)</pre>', t, re.S | re.I)
    body = m.group(1) if m else ''
    body = re.sub(r'<[^>]*>', ' ', body)
    return clean(html.unescape(body))
def wikitext(t):
    t = html.unescape(t)
    t = re.sub(r'\{\{[^{}]*\}\}', ' ', t)
    t = re.sub(r'\[\[(?:वर्गः|Category)[^\]]*\]\]', ' ', t)
    t = re.sub(r'\[\[[^\]|]*\|([^\]]*)\]\]', r'\1', t)
    t = re.sub(r'\[\[([^\]]*)\]\]', r'\1', t)
    t = re.sub(r'<[^>]*>', ' ', t)
    t = re.sub(r"'''?", '', t)
    return clean(t)
def hist_revs(path):
    t = open(path, encoding='utf-8').read()
    out = {}
    for page in re.findall(r'<title>.*?</page>', t, re.S):
        title = re.search(r'^<title>(.*?)</title>', page).group(1)
        revs = []
        for rev in re.findall(r'<revision>(.*?)</revision>', page, re.S):
            ts = re.search(r'<timestamp>(.*?)</timestamp>', rev).group(1)
            txt = re.search(r'<text[^>]*>(.*?)</text>', rev, re.S)
            revs.append((ts, wikitext(txt.group(1)) if txt else ''))
        out[title] = revs
    return out
def toks(t, keep_avagraha=True):
    t = t.replace('ऽ', ' ऽ ' if False else 'ऽ')
    t = re.sub(PUNCT, ' ', t)
    return t.split()
