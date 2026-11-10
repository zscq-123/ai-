"""Run once on the target host. Credentials stay in root-only shared files."""
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

os.umask(0o077)
ROOT=Path(__file__).resolve().parent
SHARED=Path("/opt/support-suite/shared")
SHARED.mkdir(parents=True,exist_ok=True)

def run(args, data=None):
    result=subprocess.run(args,input=data,text=True,capture_output=True)
    if result.returncode:
        (SHARED/'provision-error.log').write_text(result.stderr)
        raise RuntimeError('Provisioning failed; details in root-only shared/provision-error.log')
    return result.stdout

def container_env(name):
    return dict(item.split("=",1) for item in json.loads(run(["docker","inspect",name]))[0]["Config"]["Env"] if "=" in item)

def env_file(name, values):
    (SHARED/name).write_text("".join(f"{key}={value}\n" for key,value in values.items()))

credentials=SHARED/"credentials.json"
if not credentials.exists():
    values={key:secrets.token_hex(32) for key in ["mysql","postgres","redis","jwt","internal","open_api","callback","ai_oms","ai_buzud","ai_context","ai_tools","buzud_jwt","buzud_admin_key","web_session"]}
    values.update(json.loads((SHARED/"bootstrap.json").read_text()))
    credentials.write_text(json.dumps(values))
values=json.loads(credentials.read_text())

if not (SHARED/"databases-ready").exists():
    mysql=container_env("diy-mysql-prod")
    sql=f"CREATE USER 'support_oms'@'%' IDENTIFIED BY '{values['mysql']}';\n"
    for name in ["oms_user","oms_order","oms_inventory","oms_after_sales","oms_payment","oms_integration"]:
        # Abort before creating anything if a previous deployment owns these names.
        check=run(["docker","exec","-e",f"MYSQL_PWD={mysql['MYSQL_ROOT_PASSWORD']}","diy-mysql-prod","mysql","-uroot","-N","-e",f"SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='{name}'"])
        if check.strip(): raise RuntimeError(f"Database already exists: {name}; inspect before provisioning")
        sql+=f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; GRANT ALL ON `{name}`.* TO 'support_oms'@'%';\n"
    run(["docker","exec","-i","-e",f"MYSQL_PWD={mysql['MYSQL_ROOT_PASSWORD']}","diy-mysql-prod","mysql","-uroot"],sql)
    pg=container_env("nova-preview-postgres-1")
    run(["docker","exec","-i","nova-preview-postgres-1","psql","-v","ON_ERROR_STOP=1","-U",pg["POSTGRES_USER"],"-d",pg["POSTGRES_DB"]],
        f"CREATE USER support_buzud PASSWORD '{values['postgres']}';\nCREATE DATABASE support_buzud OWNER support_buzud;\n")
    (SHARED/"databases-ready").touch()

ai=container_env("nova-preview-ai-service-1")
env_file("ai.env",{"AI_ENVIRONMENT":"production","AI_PROVIDER":"deepseek","AI_MODEL":"deepseek-flash","AI_MODEL_BASE_URL":"https://api.deepseek.com","DEEPSEEK_API_KEY":ai["DEEPSEEK_API_KEY"],"AI_PERSIST_CONVERSATIONS":"false","AI_TRUSTED_CONTEXT_SECRET":values["ai_context"],"AI_COMMERCE_TOOL_SECRET":values["ai_tools"],"AI_OMS_INTEGRATION_SECRET":values["ai_oms"],"AI_BUZUD_INTEGRATION_SECRET":values["ai_buzud"]})
env_file("oms.env",{"MYSQL_PASSWORD":values["mysql"],"REDIS_PASSWORD":values["redis"],"OMS_JWT_SECRET":values["jwt"],"OMS_INTERNAL_SERVICE_SECRET":values["internal"],"OMS_OPEN_API_DEMO_MALL_SECRET":values["open_api"],"OMS_MALL_CALLBACK_SECRET":values["callback"],"NOVA_AI_SECRET":values["ai_oms"]})
env_file("buzud.env",{"DB_PASSWORD":values["postgres"],"IKEA_JWT_SECRET":values["buzud_jwt"],"IKEA_ADMIN_KEY":values["buzud_admin_key"],"NOVA_AI_SECRET":values["ai_buzud"]})
env_file("web.env",{"ADMIN_USERNAME":"admin","ADMIN_PASSWORD":values["web_admin_password"],"ADMIN_SECRET":values["web_session"],"IKEA_ADMIN_KEY":values["buzud_admin_key"]})
(SHARED/"redis.conf").write_text(f"bind 0.0.0.0\nprotected-mode yes\nrequirepass {values['redis']}\nappendonly yes\nmaxmemory 32mb\nmaxmemory-policy noeviction\n")
(SHARED/"redis.conf").chmod(0o644)
(SHARED/"redis").mkdir(exist_ok=True)
if not (SHARED/"cms-data").exists():
    shutil.copytree(ROOT/"cms-seed",SHARED/"cms-data")
for path in [SHARED/"cms-data",*(SHARED/"cms-data").rglob("*")]:
    os.chown(path,1000,1000)
    path.chmod(0o755 if path.is_dir() else 0o644)
print("Isolated databases and protected service configuration ready")
