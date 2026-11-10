"""Start one JVM at a time and require its health check before proceeding."""
import json
import subprocess
import time
from urllib.request import urlopen

for name,port in [('user-service',8081),('oms-gateway',8080),('order-service',8082),('inventory-service',8083),('buzud-api',8090),('after-sales-service',8084),('payment-center',8085),('integration-service',8086)]:
    subprocess.run(['docker','compose','-f','compose.json','up','-d',name],check=True)
    for attempt in range(48):
        try:
            info=json.loads(subprocess.check_output(['docker','inspect','support-suite-'+name+'-1']))[0]
            ip=info['NetworkSettings']['Networks']['support-suite_default']['IPAddress']
            route='/api/v1/products' if name=='buzud-api' else '/actuator/health'
            with urlopen(f'http://{ip}:{port}{route}',timeout=4) as response:
                assert response.status==200
                if name!='buzud-api': assert json.load(response)['status']=='UP'
            print(name+' ready',flush=True)
            break
        except Exception:
            time.sleep(5)
    else:
        raise RuntimeError(name+' failed readiness; remaining services not started')
subprocess.run(['docker','exec','support-suite-gateway','nginx','-s','reload'],check=True)
