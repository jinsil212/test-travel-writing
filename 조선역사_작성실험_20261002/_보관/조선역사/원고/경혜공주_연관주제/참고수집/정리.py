import pathlib, re, json
p=pathlib.Path(__file__).parent
v=next(p.glob('*.ko-orig.vtt')).read_text(encoding='utf-8')
out=[]
for line in v.splitlines():
    if not line.strip() or '-->' in line or line.startswith(('WEBVTT','Kind:','Language:')): continue
    s=re.sub('<[^>]+>','',line).strip()
    if s and (not out or s!=out[-1]): out.append(s)
(p/'원문.txt').write_text('\n'.join(out),encoding='utf-8')
print(len(out),len('\n'.join(out)))
