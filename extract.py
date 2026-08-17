import zipfile, re, os
src = r'D:\HƯỚNG DẪN ROP TRÊN CASIO fx-580VNX.docx'
out = r'D:\Casiobot\doc_extracted.txt'
with zipfile.ZipFile(src) as z:
    xml = z.read('word/document.xml').decode('utf-8', errors='replace')
# lấy text theo từng <w:p> (đoạn)
paras = re.findall(r'<w:p[ >].*?</w:p>', xml, re.S)
lines = []
for p in paras:
    texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.S)
    line = ''.join(texts)
    lines.append(line)
content = '\n'.join(lines)
with open(out, 'w', encoding='utf-8') as f:
    f.write(content)
print('so doan:', len(lines))
print('tong ky tu:', len(content))
print('--- 30 doan dau ---')
print('\n'.join(l for l in lines[:30] if l.strip()))
