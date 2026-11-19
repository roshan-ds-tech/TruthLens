# Deployment

| Part | Where | How it updates |
|---|---|---|
| UI (React, `dist/`) | Vercel | Vercel's GitHub integration builds every push (`vercel.json`) |
| Analysis API (FastAPI, Docker) | Hugging Face Space (free CPU, 16 GB RAM) | `.github/workflows/deploy-backend.yml` after CI passes on `main` |

## One-time setup

1. **Hugging Face**: create a free account and a token with *write* access (huggingface.co → Settings → Access Tokens).
2. **GitHub** (repo → Settings → Secrets and variables → Actions):
   - secret `HF_TOKEN` = that token
   - variable `HF_SPACE` = `<hf-user>/truthlens-api` (the workflow creates the Space if it does not exist)
   - variable `FRONTEND_ORIGINS` = your Vercel URL, e.g. `https://truthlens.vercel.app`
   - variable `FRONTEND_ORIGIN_REGEX` = `https://truthlens-.*\.vercel\.app` (optional, for preview deployments)
3. **Vercel**: *Add New → Project → Import* the GitHub repo. Framework: Vite (read from `vercel.json`). Add the
   environment variable `VITE_API_BASE` = `https://<hf-user>-truthlens-api.hf.space`, then deploy.
4. Re-run the *Deploy backend to Hugging Face* workflow once (Actions tab) so the Space picks up the CORS origins.

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
