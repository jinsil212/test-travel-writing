"""Join explicit authored parts; never overwrite an existing version."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
parts = ['01_도입과효종.txt', '02_숙종의초빙.txt', '03_원자와처벌.txt', '04_사후와착지.txt']
target = root / sys.argv[1]
if target.parent != root:
    raise SystemExit('Output must be in this audit folder')
body = '\n\n'.join((root / '파트' / p).read_text(encoding='utf-8').strip() for p in parts) + '\n'
with target.open('x', encoding='utf-8', newline='\n') as handle:
    handle.write(body)
print(f'{target}\ncharacters={len(body)}')
