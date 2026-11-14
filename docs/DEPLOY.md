# Deploying Proveryai

Two parts: the web app on Vercel, the API on a Hetzner server. The API cannot run on Vercel: an audit clones a repo, starts Chromium and streams progress for up to a few minutes.

| Part | Where | Address |
|---|---|---|
| Web (`web/`) | Vercel | `https://proveryai.babarika.dev` |
| API (`api/`) | Hetzner, Docker + Caddy | `https://proveryai-api.babarika.dev` |

`babarika.dev` itself stays as it is; both addresses are new subdomains. DNS for the domain is on Cloudflare.

Deploy from `main`, so merge what you want judges to see first.

## 1. API on Hetzner

1. In the Hetzner Cloud console create a server: Ubuntu 24.04, shared vCPU, 2 vCPU / 4 GB RAM (Chromium needs the memory), your SSH key. Add a firewall that allows inbound TCP 22, 80 and 443.
2. In Cloudflare DNS add an `A` record: name `proveryai-api`, value the server's IPv4, proxy status **DNS only** (grey cloud). Caddy needs a direct connection to get its certificate.
3. On the server:

```sh
ssh root@SERVER_IP
curl -fsSL https://get.docker.com | sh
git clone https://github.com/AlexAlexBabarika/Eurasian-Hack-14-Nov.git proveryai
cd proveryai
cp .env.example .env                 # add LLM_API_KEY, or leave it empty for heuristics only
cp deploy/.env.example deploy/.env   # check API_DOMAIN and WEB_ORIGIN
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
```

The first build takes several minutes (it downloads Chromium).

4. Check it: `curl https://proveryai-api.babarika.dev/health` should return `{"ok":true,"demo_mode":"cached"}`.

`deploy/docker-compose.yml` sets `PUBLIC_MODE=1` (local paths and private addresses are refused), `DEMO_MODE=cached` (the demo buttons and the saved examples replay stored audits) and `WEB_ORIGINS` (CORS). These override the same names in `.env`.

To update: `git pull && docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build`.

Logs: `docker compose -f deploy/docker-compose.yml --env-file deploy/.env logs -f api`.

### The LLM key is public spend

The API has no login and no rate limit. Anyone who finds the address can start audits, and each one with an LLM key makes about ten model calls. Before sharing the link, either set a spend limit on the key at your provider, or leave `LLM_API_KEY` empty (the pipeline then uses keyword heuristics and template text).

## 2. Web on Vercel

1. vercel.com > Add New > Project > import `AlexAlexBabarika/Eurasian-Hack-14-Nov`.
2. Root Directory: `web`. Framework is detected as Next.js. Leave "Include files outside the root directory in the Build Step" on: the build imports the two demo audits from `api/data/audits/`.
3. Environment variable: `NEXT_PUBLIC_API_URL` = `https://proveryai-api.babarika.dev`. It is read at build time, so redeploy after changing it.
4. Deploy, then Project > Settings > Domains > add `proveryai.babarika.dev`. Vercel shows a CNAME target.
5. In Cloudflare DNS add a `CNAME` record: name `proveryai`, value the target Vercel showed, proxy status **DNS only**.

## 3. Check the public site

- `https://proveryai.babarika.dev` loads, and the example audits open.
- "Use demo fixture" then "Run" replays the saved audit of the demo product. The form shows `localhost:4100` addresses; that is expected, they are the key of the saved audit.
- A real audit works: any public GitHub repo, its site and its policy URL.
- If the form reports "Cannot reach the audit service", `NEXT_PUBLIC_API_URL` or `WEB_ORIGIN` is wrong. They must match exactly, with `https://` and no trailing slash.

## 4. Repository page

```sh
gh repo edit AlexAlexBabarika/Eurasian-Hack-14-Nov \
  --description "Proveryai: checks a privacy policy against what the code and live site actually do, under UK, EU and Kazakhstan law" \
  --homepage https://proveryai.babarika.dev
```

## Everything on one server instead

If you would rather skip Vercel, add a second site to `deploy/Caddyfile` and run `pnpm build && pnpm start` for `web/` on the same server. Vercel is less work and is the route tested here (`pnpm build` passes with the production API address).
