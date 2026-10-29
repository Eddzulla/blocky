# Deployment Plan: Ubuntu Server

Goal: run blocky continuously on your Ubuntu server, scheduled instead of manual, reachable remotely via a free DNS name, with the server hardened against unauthorized access.

This is a plan to review and implement step by step — nothing here has been built yet.

---

## 1. Containerize for production

Right now `docker-compose.yml` only runs `db` + `adminer`; the API runs via local `uvicorn --reload` and the frontend via `npm run dev`. Neither is meant for a server. Target shape (already sketched in `PLAN.md`):

```
docker-compose.yml
  db       postgres:17 (unchanged)
  api      FastAPI + uvicorn, no --reload
  web      built React app served by Caddy, proxying /api/* to api
```

Needed:
- **`Dockerfile` for the API**: Python base image, install deps, `CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]`.
- **`Dockerfile` for the frontend**: multi-stage — `npm run build` in a node image, then copy `dist/` into a Caddy (or nginx) image.
- **`frontend/.env` for production**: set `VITE_API_URL=/api` (a relative path, not a hardcoded domain). Vite bakes this in at *build time*, so a relative path means the same built image works regardless of what domain ends up pointing at the server — the reverse proxy forwards `/api/*` to the `api` container.
- Postgres and Adminer stay **off** the public-facing ports — only `web` (Caddy) is exposed.

## 2. Get it onto the server

```bash
# one-time setup on the Ubuntu server
curl -fsSL https://get.docker.com | sh          # installs Docker + Compose plugin
sudo usermod -aG docker $USER                   # re-login after this

git clone <your repo> blocky
cd blocky
# create .env and frontend/.env fresh here — never commit these
docker compose up -d --build
docker compose exec api alembic upgrade head
```

## 3. Scheduling (replaces manual runs)

On a real Linux server, **systemd timers** are the natural fit — better than cron for this: built-in logging via `journalctl`, retry/failure handling, and `docker compose` dependency ordering.

`/etc/systemd/system/blocky-pipeline.service`:
```ini
[Unit]
Description=Blocky full fetch

[Service]
Type=oneshot
WorkingDirectory=/home/<user>/blocky
ExecStart=/usr/bin/docker compose exec -T api python -m app.pipeline
```

`/etc/systemd/system/blocky-pipeline.timer`:
```ini
[Unit]
Description=Run blocky full fetch every 6 hours

[Timer]
OnCalendar=*-*-* 00,06,12,18:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Same pattern for `blocky-quick-pipeline.service`/`.timer` running `python -m app.quick_pipeline`, on whatever interval you land on (every 1–3 hours, per our earlier discussion). Enable both with `sudo systemctl enable --now blocky-pipeline.timer blocky-quick-pipeline.timer`.

## 4. Free DNS so it's reachable remotely

Two parts: a name that resolves to your server, and HTTPS so browsers don't complain.

- **If this is a home server behind a router**: your ISP almost certainly gives you a dynamic (changing) public IP. Use **[DuckDNS](https://www.duckdns.org/)** (free) — it gives you `yourname.duckdns.org` and a tiny script/cron job that keeps it pointed at your current IP whenever it changes. Then port-forward **80 and 443** on your router to the server's local IP — nothing else.
- **If this is a cloud VPS**: it already has a static public IP — point any free DNS (DuckDNS works here too, or your VPS provider's own DNS if offered) directly at it. No port-forwarding needed, you own the box's network already.
- **HTTPS**: use **[Caddy](https://caddyserver.com/)** as the reverse proxy in front of `web`/`api` — it gets you free, auto-renewing Let's Encrypt certificates with essentially zero config (a `Caddyfile` with just your domain and the two proxy rules), which is simpler to run correctly than nginx + certbot.

## 5. Protecting the server

This matters more once something is actually reachable from the internet:

- **Firewall (`ufw`)**: allow only what's needed — `80`, `443`, and SSH. Deny everything else by default, so Postgres (5432) and Adminer (8080) are never reachable publicly even if someone finds the IP.
  ```bash
  sudo ufw default deny incoming
  sudo ufw allow 80,443/tcp
  sudo ufw allow 22/tcp   # or skip this — see Tailscale below
  sudo ufw enable
  ```
- **SSH hardening**: key-only auth (`PasswordAuthentication no` in `sshd_config`), disable root login.
- **fail2ban**: bans IPs after repeated failed SSH attempts — cheap insurance against brute-forcing.
- **Automatic security updates**: `sudo apt install unattended-upgrades` — keeps the OS patched without you remembering to.
- **Consider Tailscale for admin access** (already noted as an idea in `PLAN.md`): join the server to a private Tailscale network (free for personal use) and do SSH, Adminer, and any admin work over that instead of the public internet. That means you can drop port 22 from the public firewall rule entirely — the *only* thing exposed to the internet is the Blocky web app itself (via Caddy on 80/443), which is exactly what you want "reachable on the go," while everything administrative has zero public attack surface. This is the combination I'd actually recommend: **public DNS + Caddy for the app, Tailscale for everything else.**

## 6. Backups (carried over from `PLAN.md`'s "Later: production" notes)

A systemd timer (same pattern as above) running:
```bash
docker compose exec -T db pg_dump -U blocky blocky > backups/blocky-$(date +%F).sql
```
Daily is plenty given how often the data actually changes.

---

## Open questions for you to decide before I implement anything

1. **Home server behind a router, or a cloud VPS?** Changes whether port-forwarding is needed (step 4).
2. **Caddy or nginx** for the reverse proxy? I'd default to Caddy for the automatic HTTPS, but say so if you have a preference.
3. Want **Tailscale** set up as part of this, or keep SSH on the public port with just `ufw`/`fail2ban`?

Once you've got the server itself set up and reachable (even just via SSH), tell me and we'll go through this step by step rather than all at once.
