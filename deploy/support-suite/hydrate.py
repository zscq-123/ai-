"""Restore exact dependency/asset bytes from public sources, validating SHA-256."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import time
from urllib.request import urlopen, Request
from urllib.parse import quote
import zipfile

ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'dependency-cache'
CACHE.mkdir(exist_ok=True)

def valid(path,digest):
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest

def download(url,dest,digest):
    if valid(dest,digest): return
    dest.parent.mkdir(parents=True,exist_ok=True)
    temp=dest.with_name(dest.name+'.download')
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={'User-Agent':'Support-suite-deployment/1.0'}),timeout=45) as response, temp.open('wb') as output:
                shutil.copyfileobj(response,output)
            if not valid(temp,digest): raise ValueError('SHA-256 mismatch')
            temp.replace(dest)
            return
        except Exception:
            if attempt==2: raise
            time.sleep(1)

manifest=json.loads((ROOT/'jar-manifest.json').read_text())
def lib(item):
    digest,info=item
    dest=CACHE/digest
    if info['url']: download(info['url'],dest,digest)
    else:
        shutil.copy2(ROOT/'local-libs'/digest,dest)
        assert valid(dest,digest)
with ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(lib,manifest['libs'].items()))
(ROOT/'jars').mkdir(exist_ok=True)
for name,entries in manifest['jars'].items():
    if not (ROOT/'jar-bases'/name).exists():
        continue  # Dependencies can be prefetched while the application upload runs.
    dest=ROOT/'jars'/name
    shutil.copy2(ROOT/'jar-bases'/name,dest)
    with zipfile.ZipFile(dest,'a') as jar:
        for entry in entries:
            jar.write(CACHE/entry['sha256'],entry['path'],compress_type=zipfile.ZIP_STORED)
    dest.chmod(0o644)
print(f"Restored {len(manifest['jars'])} application jars; dependency hashes verified",flush=True)

def asset(item):
    dest=ROOT/'web-app/public'/item['path']
    try:
        download('https://medical-sg.com/'+quote(item['path']),dest,item['sha256'])
        return None
    except Exception as error:
        return {'path':item['path'],'reason':str(error)}
with ThreadPoolExecutor(max_workers=8) as pool:
    failures=[value for value in pool.map(asset,json.loads((ROOT/'asset-manifest.json').read_text())) if value]
(ROOT/'asset-download-failures.json').write_text(json.dumps(failures,indent=2))
print(f"Static assets checked; {len(failures)} files require direct upload",flush=True)
