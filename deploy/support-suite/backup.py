"""Back up only this deployment's databases and settings to a protected directory."""
from datetime import datetime,timezone
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess

os.umask(0o077)
target=Path('/opt/support-suite/backups')/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
target.mkdir(parents=True)
def env(name):
    return dict(item.split('=',1) for item in json.loads(subprocess.check_output(['docker','inspect',name]))[0]['Config']['Env'] if '=' in item)
mysql=env('diy-mysql-prod'); pg=env('nova-preview-postgres-1')
commands={
    'oms.sql.gz':['docker','exec','-e','MYSQL_PWD='+mysql['MYSQL_ROOT_PASSWORD'],'diy-mysql-prod','mysqldump','-uroot','--single-transaction','--no-tablespaces','--set-gtid-purged=OFF','--databases','oms_user','oms_order','oms_inventory','oms_after_sales','oms_payment','oms_integration'],
    'buzud.sql.gz':['docker','exec','nova-preview-postgres-1','pg_dump','-U',pg['POSTGRES_USER'],'-d','support_buzud'],
}
for name,command in commands.items():
    with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE) as process, gzip.open(target/name,'wb') as output:
        shutil.copyfileobj(process.stdout,output)
        errors=process.stderr.read().decode()
        if process.wait(): raise RuntimeError('Backup failed: '+name+' '+errors[-1000:])
    with gzip.open(target/name,'rb') as check:
        while check.read(1024*1024): pass
shutil.copytree('/opt/support-suite/shared/cms-data',target/'cms-data')
for name in ['credentials.json','ai.env','oms.env','buzud.env','web.env','redis.conf']:
    shutil.copy2(Path('/opt/support-suite/shared')/name,target/name)
    (target/name).chmod(0o600)
print('Verified backup: '+str(target))
