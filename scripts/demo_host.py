#!/usr/bin/env python3
"""Run the Mac demo, connect a Quick Tunnel, and refresh the Vercel frontend."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "hosted-demo"
RUN = DATA / "run"
STATE = RUN / "state.json"
PORT = 8786
ORIGINS = "https://truthlens-six-mu.vercel.app,https://truthlens-roshan-dss-projects.vercel.app"
TEAM = "roshan-dss-projects"
PROJECT = "truthlens"


def save(state):
    STATE.write_text(json.dumps(state, indent=2) + "\n")


def alive(pid, marker):
    if not pid:
        return False
    result = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True)
    return result.returncode == 0 and marker in result.stdout


def spawn(args, name, env=None, cwd=ROOT):
    with (RUN / f"{name}.log").open("a") as log:
        return subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True).pid


def wait_for(check, seconds, message):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        result = check()
        if result:
            return result
        time.sleep(1)
    raise RuntimeError(message)


def health(url):
    try:
        if url.startswith("http://127.0.0.1:"):
            with urllib.request.urlopen(url + "/api/health", timeout=3) as response:
                return json.load(response).get("mode") == "hosted"
        result = subprocess.run(["curl", "-fsS", "--max-time", "5", url + "/api/health"],
                                capture_output=True, text=True)
        if result.returncode == 6:
            # Some local resolvers cache NXDOMAIN for newly created tunnel names.
            result = subprocess.run(["curl", "-fsS", "--max-time", "5", "--doh-url",
                                     "https://cloudflare-dns.com/dns-query", url + "/api/health"],
                                    capture_output=True, text=True)
        return result.returncode == 0 and json.loads(result.stdout).get("mode") == "hosted"
    except (OSError, ValueError):
        return False


def auth_file():
    candidates = [Path.home() / "Library/Application Support/com.vercel.cli/auth.json",
                  Path.home() / ".local/share/com.vercel.cli/auth.json"]
    return next((p for p in candidates if p.exists()), candidates[0])


def vercel(path, body=None, retry=True):
    token = json.loads(auth_file().read_text())["token"]
    url = "https://api.vercel.com" + path + ("&" if "?" in path else "?") + "slug=" + TEAM
    args = ["curl", "-sS", "--max-time", "60", "--config", "-", url]
    if body is not None:
        args += ["-X", "POST", "--data-binary", json.dumps(body)]
    # Pass credentials through stdin, never command arguments or console output.
    config = f'header = "Authorization: Bearer {token}"\nheader = "Content-Type: application/json"\n'
    response = subprocess.run(args, input=config, capture_output=True, text=True, check=True)
    result = json.loads(response.stdout)
    error = result.get("error")
    if error and error.get("invalidToken") and retry:
        subprocess.run(["npx", "--yes", "vercel@66.2.0", "whoami"], check=True)
        return vercel(path, body, retry=False)
    if error:
        raise RuntimeError(error.get("message", "Vercel request failed"))
    return result


def connect_frontend(state):
    project = vercel("/v9/projects/" + PROJECT)
    project_id = project["id"]
    vercel(f"/v10/projects/{project_id}/env?upsert=true", {
        "key": "VITE_API_BASE", "value": state["api_url"], "type": "plain",
        "target": ["production", "preview", "development"],
    })
    link = project["link"]
    deploy = vercel("/v13/deployments", {
        "name": PROJECT, "project": project_id, "target": "production",
        "gitSource": {"type": "github", "repoId": str(link["repoId"]),
                      "ref": link.get("productionBranch", "main")},
        "projectSettings": {key: project[key] for key in
                            ("framework", "buildCommand", "outputDirectory")},
    })
    state["deployment_id"] = deploy["id"]
    save(state)
    print("Vercel is rebuilding with the new tunnel URL...", flush=True)

    def ready():
        result = vercel("/v13/deployments/" + deploy["id"])
        if result.get("readyState") in ("ERROR", "CANCELED"):
            raise RuntimeError(result.get("errorMessage") or "Vercel deployment failed")
        return result if result.get("readyState") == "READY" else None

    result = wait_for(ready, 300, "Vercel is still building; use the deployment dashboard to check it.")
    state["frontend_url"] = "https://truthlens-six-mu.vercel.app"
    state["deployment_url"] = "https://" + result["url"]
    save(state)


def start():
    RUN.mkdir(parents=True, exist_ok=True)
    os.chmod(DATA, 0o700)
    old = json.loads(STATE.read_text()) if STATE.exists() else {}
    if alive(old.get("backend_pid"), "uvicorn") or alive(old.get("tunnel_pid"), "cloudflared"):
        raise RuntimeError("A demo process is already running. Use status or stop first.")
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", PORT)) == 0:
            raise RuntimeError(f"Port {PORT} is occupied; no existing process was changed.")
    tunnel = shutil.which("cloudflared")
    if not tunnel:
        raise RuntimeError("Install the tunnel client first: brew install cloudflared")
    if not auth_file().exists():
        raise RuntimeError("Sign in to Vercel first: npx vercel login")
    env = dict(os.environ, TRUTHLENS_MODE="hosted", TRUTHLENS_DATA=str(DATA),
               TRUTHLENS_ALLOWED_ORIGINS=ORIGINS, TRUTHLENS_ALLOWED_ORIGIN_REGEX="",
               TRUTHLENS_ALLOW_SIGNUP="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
               DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib")
    state = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "data_dir": str(DATA), "port": PORT}
    state["backend_pid"] = spawn([str(ROOT / "backend/.venv/bin/python"), "-m", "uvicorn",
                                  "app.main:app", "--host", "127.0.0.1", "--port", str(PORT),
                                  "--workers", "1"], "backend", env, ROOT / "backend")
    save(state)
    wait_for(lambda: health(f"http://127.0.0.1:{PORT}"), 60, "Backend did not start; see backend.log.")
    state["awake_pid"] = spawn(["/usr/bin/caffeinate", "-i", "-w", str(state["backend_pid"])], "awake")
    # A fresh log prevents accidentally reusing a previous Quick Tunnel hostname.
    (RUN / "tunnel.log").write_text("")
    state["tunnel_pid"] = spawn([tunnel, "tunnel", "--url", f"http://127.0.0.1:{PORT}",
                                 "--protocol", "http2", "--no-autoupdate"], "tunnel")
    save(state)

    def hostname():
        match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", (RUN / "tunnel.log").read_text())
        return match.group() if match else None

    state["api_url"] = wait_for(hostname, 90, "Tunnel did not start; see tunnel.log.")
    save(state)
    print("Backend: " + state["api_url"], flush=True)
    wait_for(lambda: health(state["api_url"]), 90, "Public tunnel is not responding; see tunnel.log.")
    connect_frontend(state)
    print("Frontend: " + state["frontend_url"])
    print("Keep this Mac awake, online, and its lid open. Stop with: python3 scripts/demo_host.py stop")


def stop(state):
    for key, marker in (("tunnel_pid", "cloudflared"), ("backend_pid", "uvicorn"), ("awake_pid", "caffeinate")):
        if alive(state.get(key), marker):
            try:
                os.kill(state[key], signal.SIGTERM)
            except ProcessLookupError:
                pass
    state["stopped_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save(state)
    print("Demo stopped. Accounts and cases remain in " + str(DATA))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "status", "stop", "connect"])
    action = parser.parse_args().action
    try:
        if action == "start":
            start()
        else:
            state = json.loads(STATE.read_text())
            if action == "stop":
                stop(state)
            elif action == "connect":
                if not health(state.get("api_url", "")):
                    raise RuntimeError("The public backend is offline. Start the demo first.")
                connect_frontend(state)
                print("Frontend: " + state["frontend_url"])
            else:
                print(json.dumps(dict(state,
                      backend_running=alive(state.get("backend_pid"), "uvicorn"),
                      tunnel_running=alive(state.get("tunnel_pid"), "cloudflared")), indent=2))
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"{exc}\nLogs and process state: {RUN}\n")
