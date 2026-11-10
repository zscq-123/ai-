"""Create the first platform admin only after the new user schema is migrated."""
import json
import subprocess
from pathlib import Path

shared=Path('/opt/support-suite/shared')
values=json.loads((shared/'credentials.json').read_text())
env=dict(item.split('=',1) for item in json.loads(subprocess.check_output(['docker','inspect','diy-mysql-prod']))[0]['Config']['Env'] if '=' in item)
command=['docker','exec','-i','-e',f"MYSQL_PWD={env['MYSQL_ROOT_PASSWORD']}",'diy-mysql-prod','mysql','-uroot','oms_user']
sql="INSERT INTO user (username,password,real_name,user_type,status) SELECT 'admin','"+values['oms_admin_hash']+"','平台管理员',1,1 WHERE NOT EXISTS (SELECT 1 FROM user WHERE username='admin');"
result=subprocess.run(command,input=sql,text=True,capture_output=True)
if result.returncode:
    (shared/'bootstrap-error.log').write_text(result.stderr)
    (shared/'bootstrap-error.log').chmod(0o600)
    raise RuntimeError('Administrator bootstrap failed; inspect protected bootstrap-error.log')
print('Initial OMS administrator ready (random password)')
