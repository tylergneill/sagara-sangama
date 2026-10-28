import re, unicodedata
CONS = 'kgcjṭḍtdpbṅñṇnmyrlvśṣsh'
def ortho(s):
    s = unicodedata.normalize('NFC', s).lower()
    s = s.replace('‍','').replace('‌','')
    s = re.sub(r"['’‘`ऽ]", '', s)
    s = s.replace('ḻ', 'l').replace('kś', 'kṣ').replace('m̐', 'ṃ')
    s = re.sub(r'ṅ(?=\s*[kg])|ñ(?=\s*[cj])|ṇ(?=\s*[ṭḍ])|n(?=\s*[td])|m(?=\s*[pb])', 'ṃ', s)
    s = re.sub(r'm(?=\s|$)', 'ṃ', s)
    s = re.sub(r'[^a-zāīūṛṝḷḹēōṃḥṅñṭḍṇśṣ]', '', s)
    return s
