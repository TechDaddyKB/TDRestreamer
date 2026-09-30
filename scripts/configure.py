#!/usr/bin/env python3
"""Generate local configuration without printing secrets or replacing existing files."""
import base64
import os
from pathlib import Path
import secrets
p=Path('.env')
values={'POSTGRES_PASSWORD':secrets.token_hex(32),'TDR_DB_PASSWORD':secrets.token_hex(32),'TDR_ROOT_KEY':base64.b64encode(secrets.token_bytes(32)).decode(),'TDR_BOOTSTRAP_TOKEN':secrets.token_urlsafe(32),'TDR_METRICS_TOKEN':secrets.token_urlsafe(32),'TDR_BIND':'127.0.0.1','TDR_PORT':'8080'}
fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f:
 for k,v in values.items():f.write(f'{k}={v}\n')
print('Created .env with mode 0600. Read the setup credential locally when configuring the UI.')
