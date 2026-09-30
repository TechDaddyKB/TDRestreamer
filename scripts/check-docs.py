#!/usr/bin/env python3
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
ledger=(root/'docs/requirements.md').read_text()
for prefix,count in [('R',50),('A',22)]:
 for n in range(1,count+1):assert f'| {prefix}{n:02d} |' in ledger, f'missing {prefix}{n:02d}'
for p in [root/'README.md',*list((root/'docs').rglob('*.md'))]:
 for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' in link or link.startswith('#'):continue
  path=(p.parent/link.split('#')[0])
  assert path.exists(),f'{p}: missing {link}'
assert (root/'LICENSE').stat().st_size>30000
print('Documentation links, license and all 72 ledger entries verified.')
