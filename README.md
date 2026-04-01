# axflo

## Deploy on Vercel (Flask)

This project is configured for Vercel with:

- `api/index.py` as the serverless entrypoint
- `vercel.json` routing all requests to Flask

### 1. Push code to GitHub

Make sure these files are committed:

- `app.py`
- `requirements.txt`
- `api/index.py`
- `vercel.json`

### 2. Import project in Vercel

1. Go to Vercel Dashboard.
2. Click **Add New -> Project**.
3. Import your GitHub repository.
4. Keep root directory as the repository root.
5. Click **Deploy**.

### 3. Add Environment Variables in Vercel

In **Project Settings -> Environment Variables**, add:

- `DATABASE_URL` (use a managed Postgres URL in production)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Important:

- Do not use local SQLite for production data on Vercel.
- Vercel serverless file storage is ephemeral, so DB writes must go to external DB.

### 4. Connect your custom domain

In **Project Settings -> Domains**:

1. Add your domain (example: `axflo.in`).
2. Add `www` subdomain (example: `www.axflo.in`).
3. In your DNS provider, configure records exactly as shown by Vercel:
	- Usually `A` record for apex (`@`) to `76.76.21.21`
	- Usually `CNAME` for `www` to `cname.vercel-dns.com`
4. Wait for DNS propagation (few minutes up to 24 hours).
5. Set primary domain in Vercel (either apex or `www`).

### 5. Re-deploy after env vars

After setting env vars/domain, trigger a redeploy from Vercel Deployments tab.

## Local run

```bash
pip install -r requirements.txt
python app.py
```

Deployment marker: 2026-04-02