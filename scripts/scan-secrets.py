#!/usr/bin/env python3
"""Small tracked-file tripwire, not a replacement for comprehensive security review."""
from pathlib import Path
import re
import subprocess
files=subprocess.check_output(['git','ls-files','-z']).decode().split('\0')
patterns=[r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{50,}',r'AKIA[0-9A-Z]{16}',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
issues=[]
for name in filter(None,files):
 p=Path(name)
 if not p.exists():continue
 if p.name.startswith('.env') and not p.name.endswith('.example'):issues.append(name)
 try:text=p.read_text()
 except UnicodeError:continue
 if any(re.search(pattern,text) for pattern in patterns):issues.append(name)
if issues:raise SystemExit('Potential secrets in tracked files: '+', '.join(issues))
print('Tracked-file secret tripwire passed; staged content still requires review.')
