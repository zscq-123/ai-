"""Generate a secret-free Compose manifest for this small, existing server."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARED = "/opt/support-suite/shared"
JAVA = "-Xms32m -Xmx112m -XX:MaxMetaspaceSize=128m -XX:ReservedCodeCacheSize=24m -XX:MaxDirectMemorySize=16m -Xss512k -XX:+UseSerialGC -XX:ActiveProcessorCount=1 -Duser.home=/tmp -Dcsp.sentinel.log.dir=/tmp/sentinel"
PORTS = {"oms-gateway":8080, "user-service":8081, "order-service":8082,
         "inventory-service":8083, "after-sales-service":8084, "payment-center":8085,
         "integration-service":8086}
common = {"restart":"unless-stopped", "logging":{"driver":"json-file", "options":{"max-size":"10m","max-file":"2"}}, "networks":["default"]}
services = {}
static = {"spring":{"cloud":{"discovery":{"client":{"simple":{"instances":{
    name:[{"uri":f"http://{name}:{port}"}] for name,port in PORTS.items() if name != "oms-gateway"
}}}}}}}
for name,port in PORTS.items():
    env = {
        "JAVA_TOOL_OPTIONS":JAVA,"SERVER_PORT":str(port),"SPRING_PROFILES_ACTIVE":"server",
        "SPRING_CONFIG_IMPORT":"optional:file:/app/none.properties",
        "SPRING_CLOUD_NACOS_DISCOVERY_ENABLED":"false","SPRING_CLOUD_NACOS_CONFIG_ENABLED":"false",
        "SPRING_CLOUD_NACOS_CONFIG_IMPORT_CHECK_ENABLED":"false",
        "SPRING_CLOUD_SENTINEL_ENABLED":"false","SPRING_CLOUD_GATEWAY_SERVER_WEBFLUX_DISCOVERY_LOCATOR_ENABLED":"false",
        "SPRING_APPLICATION_JSON":json.dumps(static,separators=(",",":")),
        "SPRING_DATASOURCE_HIKARI_MAXIMUM_POOL_SIZE":"3","SPRING_DATASOURCE_HIKARI_MINIMUM_IDLE":"1",
        "SERVER_TOMCAT_THREADS_MAX":"16","SERVER_TOMCAT_THREADS_MIN_SPARE":"2",
        "MANAGEMENT_ENDPOINTS_WEB_EXPOSURE_INCLUDE":"health,info","MANAGEMENT_ENDPOINT_HEALTH_SHOW_DETAILS":"never",
        "SPRINGDOC_API_DOCS_ENABLED":"false","SPRINGDOC_SWAGGER_UI_ENABLED":"false",
        "MYSQL_HOST":"support-mysql","MYSQL_USERNAME":"support_oms","REDIS_HOST":"support-redis",
        "OMS_SEED_DEMO_DATA":"false","OMS_SENTINEL_ENABLED":"false",
        "OMS_INVENTORY_URL":"http://inventory-service:8083","OMS_PAYMENT_URL":"http://payment-center:8085",
        "OMS_ORDER_URL":"http://order-service:8082","OMS_INTEGRATION_NOTIFICATION_PROVIDER":"mock",
        "SPRING_MAIL_PASSWORD":"","OMS_MALL_CALLBACK_URL":"http://buzud-api:8090",
        "NOVA_AI_URL":"http://support-ai:8000","OMS_SUPPORT_GATEWAY_URL":"http://oms-gateway:8080",
    }
    services[name] = {**common,"image":"eclipse-temurin:25-jre","user":"10001:10001",
        "working_dir":"/app","command":["java","-jar","/app/service.jar"],
        "volumes":[f"./jars/{name}.jar:/app/service.jar:ro"],
        "env_file":[f"{SHARED}/oms.env"],"environment":env,"mem_limit":"320m","memswap_limit":"640m"}
    if name != "oms-gateway": services[name]["networks"]=["default","data"]
services["integration-service"]["environment"]["MANAGEMENT_HEALTH_MAIL_ENABLED"]="false"  # Notification provider is explicitly mock.
services["support-redis"]={**common,"image":"redis:7","command":["redis-server","/etc/redis/support.conf"],
    "volumes":[f"{SHARED}/redis.conf:/etc/redis/support.conf:ro",f"{SHARED}/redis:/data"],"mem_limit":"64m"}
services["support-ai"]={**common,"image":"nova-ai-service:20261105-product-price-evidence-9eda8d8",
    "entrypoint":["/opt/venv/bin/uvicorn","support_main:app","--host","0.0.0.0","--port","8000"],
    "working_dir":"/app","environment":{"PYTHONPATH":"/app/src:/app","PYTHONDONTWRITEBYTECODE":"1",
        "AI_INTEGRATION_AGENTS_ENABLED":"true","AI_AGENT_TOTAL_TIMEOUT_SECONDS":"24","AI_AGENT_CALL_TIMEOUT_SECONDS":"6","AI_AGENT_MAX_CALLS":"11"},
    "env_file":[f"{SHARED}/ai.env"],"volumes":["./ai-src:/app/src:ro","./support_main.py:/app/support_main.py:ro"],"mem_limit":"256m"}
services["buzud-api"]={**common,"image":"eclipse-temurin:25-jre","user":"10001:10001",
    "command":["java","-jar","/app/service.jar"],"env_file":[f"{SHARED}/buzud.env"],
    "environment":{"JAVA_TOOL_OPTIONS":JAVA,"SERVER_PORT":"8090","DB_HOST":"support-postgres","DB_NAME":"support_buzud","DB_USER":"support_buzud",
        "SPRING_DATASOURCE_HIKARI_MAXIMUM_POOL_SIZE":"3","SPRING_DATASOURCE_HIKARI_MINIMUM_IDLE":"1",
        "SERVER_TOMCAT_THREADS_MAX":"16","NOVA_AI_URL":"http://support-ai:8000","IKEA_CHAT_KNOWLEDGE_FILE":"/data/chat-knowledge.json",
        "CORS_ALLOWED_ORIGINS":"https://154.36.185.110:18083","BUZUD_OMS_ENABLED":"false",
        "IKEA_PAYMENT_MOCK_ONLY":"false","IKEA_YEAHPAY_ENABLED":"false","BUZUD_MARKETING_PUBLIC_BASE_URL":"https://154.36.185.110:18083",
        "BUZUD_VOUCHER_BOOKING_URL":"https://154.36.185.110:18083/zh/booking/"},
    "volumes":["./jars/buzud-api.jar:/app/service.jar:ro",f"{SHARED}/cms-data:/data:ro"],"networks":["default","data"],"mem_limit":"320m","memswap_limit":"640m"}
services["buzud-web"]={**common,"image":"node:24-alpine","user":"1000:1000","working_dir":"/app",
    "command":["node","server.js"],"env_file":[f"{SHARED}/web.env"],
    "environment":{"CMS_DATA_ROOT":"/app/src/data","NODE_OPTIONS":"--max-old-space-size=192","NODE_ENV":"production","HOSTNAME":"0.0.0.0","PORT":"3000"},
    "volumes":["./web-app:/app",f"{SHARED}/cms-data:/app/src/data"],"mem_limit":"320m"}
services["gateway"]={**common,"image":"nginx:alpine","container_name":"support-suite-gateway",
    "ports":["18083:8443","18084:8444"],"mem_limit":"64m",
    "volumes":["./nginx.conf:/etc/nginx/conf.d/default.conf:ro","./oms-web:/srv/oms:ro","/opt/nova-commerce/shared/acme/config:/etc/letsencrypt:ro"]}
manifest = {"name":"support-suite","services":services,"networks":{"default":{},"data":{"external":True,"name":"support-suite-data"}}}
(ROOT/"compose.json").write_text(json.dumps(manifest,indent=2)+"\n")
print("Wrote compose.json (no credentials)")
