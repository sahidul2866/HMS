# cPanel Backend Deployment

Use this when cPanel has **Setup Python App** / Passenger support.

## Python App

- Application root: `backend`
- Application URL: your API subdomain, for example `api-hms.example.com`
- Application startup file: `passenger_wsgi.py`
- Application entry point: `application`
- Python version: 3.11 or 3.12

## Environment

Set these in cPanel's Python app environment variables, or in `backend/.env` on the server:

```env
APP_ENV=production
DEBUG=false
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
FRONTEND_ORIGINS=https://hms.example.com
AUTO_DB_BOOTSTRAP=false
AUTO_SEED_SAMPLE_DATA=false
```

If using Neon/Supabase/remote PostgreSQL, keep the provider's SSL query parameters in `DATABASE_URL`.

## Install Dependencies

From cPanel Terminal:

```bash
cd ~/backend
source /home/CPANEL_USER/virtualenv/backend/3.12/bin/activate
pip install -r requirements.txt
```

The virtualenv path differs by host. cPanel shows the exact activation command in **Setup Python App**.

## Database

Run migrations once after upload:

```bash
cd ~/backend
source /home/CPANEL_USER/virtualenv/backend/3.12/bin/activate
python -m app.scripts.update_database
```

For migrations only:

```bash
alembic upgrade head
```

## Restart

In cPanel, click **Restart** for the Python app.

Test:

```text
https://api-hms.example.com/health/live
https://api-hms.example.com/health/ready
```
