"""Start the three local projects with isolated integration secrets and logs.

Requires existing local OMS MySQL/Redis/Nacos and BUZUD PostgreSQL containers.
Build Java jars first as documented in docs/LOCAL_SUPPORT_INTEGRATION.md.
Ctrl-C stops only the processes launched here, preserving databases.
"""

import os
import secrets
import signal
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OMS = ROOT.parent / "oms"
BUZUD = ROOT.parent / "独立站medical-sgcom/ikeas"


def main():
    for port in (18000, 8080, 8081, 8082, 8090, 5173, 3000):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit(
                    f"Port {port} is in use. Stop its existing owner before starting."
                )
    logs = ROOT / "data/integration-local"
    logs.mkdir(parents=True, exist_ok=True)
    oms_secret, buzud_secret = secrets.token_hex(32), secrets.token_hex(32)
    shared = dict(os.environ, NOVA_AI_URL="http://127.0.0.1:18000")
    services = [
        (
            "ai",
            ROOT,
            [
                str(ROOT / ".venv/bin/uvicorn"),
                "ai_service.main:app",
                "--app-dir",
                "services/ai-service/src",
                "--host",
                "127.0.0.1",
                "--port",
                "18000",
            ],
            {
                "AI_OMS_INTEGRATION_SECRET": oms_secret,
                "AI_BUZUD_INTEGRATION_SECRET": buzud_secret,
                "AI_PERSIST_CONVERSATIONS": "false",
                "AI_RETRIEVER": "keyword",
            },
        ),
        (
            "oms-user",
            OMS,
            [
                "java",
                "-Xmx384m",
                "-jar",
                "backend/user-service/target/user-service-0.1.0-SNAPSHOT.jar",
            ],
            {
                "MYSQL_PORT": "13306",
                "REDIS_PORT": "16379",
                "SERVER_PORT": "8081",
                "OMS_SEED_DEMO_DATA": "false",
            },
        ),
        (
            "oms-order",
            OMS,
            [
                "java",
                "-Xmx384m",
                "-jar",
                "backend/order-service/target/order-service-0.1.0-SNAPSHOT.jar",
            ],
            {"MYSQL_PORT": "13306", "REDIS_PORT": "16379", "SERVER_PORT": "8082"},
        ),
        (
            "oms-gateway",
            OMS,
            [
                "java",
                "-Xmx384m",
                "-jar",
                "backend/oms-gateway/target/oms-gateway-0.1.0-SNAPSHOT.jar",
            ],
            {"SERVER_PORT": "8080", "NOVA_AI_SECRET": oms_secret},
        ),
        (
            "buzud",
            BUZUD,
            ["java", "-Xmx384m", "-jar", "backend/target/ikea-server-0.1.0.jar"],
            {
                "SERVER_PORT": "8090",
                "NOVA_AI_SECRET": buzud_secret,
                "CORS_ALLOWED_ORIGINS": "http://localhost:3000,http://127.0.0.1:3000",
            },
        ),
        (
            "oms-admin",
            OMS / "frontend/admin",
            ["pnpm", "dev", "--host", "127.0.0.1"],
            {},
        ),
        (
            "storefront",
            BUZUD / "frontend",
            ["npm", "run", "dev", "--", "--hostname", "127.0.0.1"],
            {"NEXT_PUBLIC_API_BASE": "http://localhost:8090"},
        ),
    ]
    children = []
    handles = []
    try:
        for name, cwd, command, environment in services:
            log = (logs / f"{name}.log").open("a")
            handles.append(log)
            child = subprocess.Popen(
                command,
                cwd=cwd,
                env=shared | environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            children.append((name, child))
        print("OMS: http://localhost:5173/support", flush=True)
        print("BUZUD: http://localhost:3000/zh/", flush=True)
        print(f"Logs: {logs}", flush=True)
        while True:
            for name, child in children:
                if child.poll() is not None:
                    raise RuntimeError(
                        f"{name} exited ({child.returncode}); inspect {logs / (name + '.log')}"
                    )
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for _, child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    main()
