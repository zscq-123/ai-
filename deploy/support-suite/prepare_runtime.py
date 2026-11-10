"""Normalize only deployed code assets, keeping shared credential files private."""
import os
from pathlib import Path

root=Path(__file__).resolve().parent
for name in ['ai-src','oms-web','web-app']:
    directory=root/name
    if not directory.exists(): continue
    for path in [directory,*directory.rglob('*')]:
        if path.is_symlink(): continue
        path.chmod(0o755 if path.is_dir() else 0o644)
        if name=='web-app': os.chown(path,1000,1000)
