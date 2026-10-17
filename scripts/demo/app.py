"""Reach the private app the legitimate way and fetch synthetic account records.

Path: laptop -> SSM session (IAM-authenticated, logged, no inbound ports) -> private EKS API ->
RBAC-authorized port-forward -> mybank-api, which requires the lab API key.
"""

import argparse
import json
import socket
import subprocess
import time
import urllib.error
import urllib.request

from scripts.demo.kube import admin_kubectl
from scripts.demo.ops import activate, api_key, exe, outputs, step

PORT = 8080


def get(path: str, key: str | None) -> tuple[int, dict]:
    request = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}",
                                     headers={"X-API-Key": key} if key else {})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hold", action="store_true", help="Keep the access open until Ctrl+C")
    args = parser.parse_args()
    activate()
    values = outputs()
    step("Opening private access: SSM tunnel -> EKS API -> port-forward to mybank-api")
    with admin_kubectl(values) as kubectl:
        subprocess.run([exe(kubectl[0]), *kubectl[1:], "-n", "mybank", "get", "pods",
                        "-o", "wide"], check=True)
        forward = subprocess.Popen([exe(kubectl[0]), *kubectl[1:], "-n", "mybank", "port-forward",
                                    "service/mybank-api", f"{PORT}:8000"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(30):
                with socket.socket() as probe:
                    if probe.connect_ex(("127.0.0.1", PORT)) == 0:
                        break
                time.sleep(1)
            key = api_key()
            step("Without the API key the app refuses")
            print("   ", get("/accounts/acct-alice", None))
            step("With the API key: one synthetic customer's account record")
            for account in ("acct-alice", "acct-bob"):
                status, body = get(f"/accounts/{account}", key)
                print(f"    {status} {body}")
            if args.hold:
                print(f"\nApp reachable at http://127.0.0.1:{PORT} (header X-API-Key from "
                      ".cache/demo-api-key). Ctrl+C closes the tunnel.", flush=True)
                while forward.poll() is None:
                    time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            forward.terminate()


if __name__ == "__main__":
    main()
