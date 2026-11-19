# Deployment

| Part | Where | How it updates |
|---|---|---|
| UI (React, `dist/`) | Vercel | Vercel's GitHub integration builds every push (`vercel.json`) |
| Demo API (FastAPI) | Mac + temporary Cloudflare HTTPS tunnel | `python3 scripts/demo_host.py start` reconnects Vercel |
| Optional cloud API (FastAPI, Docker) | Hugging Face Space (PRO subscription required) | `.github/workflows/deploy-backend.yml` after CI passes on `main` |

## Free Mac demo

The frontend is at https://truthlens-six-mu.vercel.app. The backend runs on the Mac in hosted mode,
with separate accounts and evidence stored in `data/hosted-demo/`. Existing local cases are not exposed.

Prerequisites: `make setup`, `brew install cloudflared`, and a saved Vercel CLI login (`npx vercel login`).
The launcher targets the `truthlens` Vercel project in the `roshan-dss-projects` team.

```sh
python3 scripts/demo_host.py start
python3 scripts/demo_host.py status
python3 scripts/demo_host.py stop
```

`start` launches a single backend on `127.0.0.1:8786`, opens a Quick Tunnel, updates `VITE_API_BASE`
for the Vercel project, and deploys the frontend. It also prevents idle sleep while the backend runs.
Processes continue after the command finishes. Keep the Mac online with its lid open during the demo.
`stop` closes the tunnel and backend without deleting accounts or cases.

Quick Tunnel hostnames change after a restart. Run `start` again to reconnect and redeploy Vercel;
if only the frontend deployment failed, use `python3 scripts/demo_host.py connect` to retry it.
Logs and process IDs are in `data/hosted-demo/run/`. A failed start can leave the backend or tunnel
running for diagnosis; run `stop` before starting again. No service is installed to start at login.

Quick Tunnels are for demos, have no uptime guarantee, and stop working when the tunnel process stops:
https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/.

## One-time setup

1. **Hugging Face**: Docker Spaces on CPU Basic require a PRO subscription for personal accounts.
   Create a token with *write* access (huggingface.co → Settings → Access Tokens).
2. **GitHub** (repo → Settings → Secrets and variables → Actions):
   - secret `HF_TOKEN` = that token
   - variable `HF_SPACE` = `<hf-user>/truthlens-api` (the workflow creates the Space if it does not exist)
   - variable `FRONTEND_ORIGINS` = your Vercel URL, e.g. `https://truthlens.vercel.app`
   - variable `FRONTEND_ORIGIN_REGEX` = `https://truthlens-.*\.vercel\.app` (optional, for preview deployments)
3. **Vercel**: *Add New → Project → Import* the GitHub repo. Framework: Vite (read from `vercel.json`). Add the
   environment variable `VITE_API_BASE` = `https://<hf-user>-truthlens-api.hf.space`, then deploy.
4. Re-run the *Deploy backend to Hugging Face* workflow once (Actions tab) so the Space picks up the CORS origins.
   This workflow is currently disabled while the Mac demo is in use. Re-enable it with
   `gh workflow enable deploy-backend.yml --repo roshan-ds-tech/TruthLens` if switching back to Hugging Face.

## Behaviour in hosted mode (`TRUTHLENS_MODE=hosted`)

- Every API route except `/api/health` and `/api/auth/*` needs a session token from sign-up or log-in.
- Each case belongs to the account that opened it; other accounts get 404 for it, its evidence, media, findings and reports.
- The UI's privacy copy switches from "No data leaves this device" to "Hosted demo · visible only to your account".
- API docs (`/docs`) are disabled.
- Model files are baked into the image at build time; analysis makes no network calls.
- **Storage is not persistent on a free Space**: accounts, cases and evidence reset when the Space restarts or sleeps.
  For durable storage, enable a persistent disk on the Space and set `TRUTHLENS_DATA=/data`.
- Set `TRUTHLENS_ALLOW_SIGNUP=0` on the Space to close sign-up once your accounts exist.

## Local use is unchanged

`make setup && make run` still serves everything on `http://127.0.0.1:8000` with `TRUTHLENS_MODE=local`
(cases opened with the CLI are visible to every account on that machine).
