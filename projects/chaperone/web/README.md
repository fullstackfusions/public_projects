# Chaperone console

The public site at https://chaperone.fullstackfusions.com: sessions, the flight path, the access each session actually needed, and every change ranked by risk. React + Vite + Tailwind, Black Box palette (design in `../chaperone.md`).

It reads `/api/*`, which CloudFront sends to the API function URL (OAC) in the public view: identifiers masked, no `id=me`, no jobs (D-031).

```bash
npm install
# terminal 1: /api/* stand-in (SigV4 + the public header, like CloudFront)
CHAPERONE_API_URL=$(terraform -chdir=../infra/live output -raw api_url) AWS_PROFILE=chaperone-agent uv run --script dev_proxy.py
#   before a backend change is deployed: TABLE_NAME=chaperone ACCOUNT_ID=... uv run --script dev_proxy.py --local
# terminal 2
npm run dev
# publish (after terraform apply)
AWS_PROFILE=chaperone-agent ./deploy.sh
```
