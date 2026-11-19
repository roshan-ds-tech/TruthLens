---
title: TruthLens API
emoji: 🔍
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Multimodal forensic triage API (image, video, audio, text)
---

# TruthLens API

Analysis backend for [TruthLens](https://github.com/roshan-ds-tech/TruthLens). Deployed automatically from GitHub
by `.github/workflows/deploy-backend.yml`; do not edit this Space by hand.

Health check: `GET /api/health`. All other endpoints need an account (`POST /api/auth/signup`).
Free Spaces have no persistent disk: accounts and cases reset when the Space restarts.
