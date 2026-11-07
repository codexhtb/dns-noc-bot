# DNS NOC Bot

**Python · Telegram Bot API · Prometheus · Unbound / Linux NOC**

A small, **read-only** NOC tool for checking Unbound DNS health via Telegram. All metrics come from the Prometheus HTTP API; the bot does **not** change DNS, firewall or monitoring configuration.

[← Production Cloud & DNS engineering case](https://github.com/codexhtb/codexhtb/blob/main/projects/private-cloud-dns-observability.md) · [Pulse DNS Observability](https://github.com/codexhtb/pulse)

## Features

| Command | Information |
| --- | --- |
| `/status dns1`, `/status dns2` | Current QPS, peak QPS, errors, cache hit ratio, CPU, RAM and conntrack |
| `/status_dns1`, `/status_dns2` | Per-resolver shortcuts |
| `/health` | Health of both DNS resolvers and current traffic split |
| `/alerts` | Currently firing Prometheus alerts |
| `/compare`, `/summary` | DNS1/DNS2 QPS comparison and NOC summary |
| `/analyze dns1` | Quick capacity and cache observation |
| `/conntrack` | Proxmox/selected node connection tracking |
| `/graph dns1`, `/graph dns2`, `/overlay` | QPS plots from range queries |

`/health` and `/overlay` now operate on **DNS1 and DNS2 only**; the Proxmox node is configured separately for `/conntrack`.

## Data flow

~~~mermaid
flowchart LR
    U["Unbound DNS1 and DNS2"] --> P["Prometheus"]
    N["Node exporters"] --> P
    P --> G["Grafana"]
    P --> B["DNS NOC Bot"]
    B --> T["Authorized Telegram users / chats"]
~~~

## Configuration

Host addresses, Prometheus URL and secrets are **not hard-coded**. Copy the example and replace every sample value:

~~~bash
cp .env.example .env
chmod 600 .env
~~~

| Variable | Purpose |
| --- | --- |
| `BOT_TOKEN` | BotFather Telegram token |
| `PROM_URL` | Prometheus HTTP API base URL |
| `DNS1_NODE_EXPORTER` | DNS1 node exporter `instance` label, for example `host:9100` |
| `DNS2_NODE_EXPORTER` | DNS2 node exporter `instance` label |
| `CONNTRACK_NODE_EXPORTER` | Host used by the independent `/conntrack` command |
| `TELEGRAM_ALLOWED_USER_IDS` | Comma-separated numeric Telegram user IDs |
| `TELEGRAM_ALLOWED_CHAT_IDS` | Comma-separated numeric Telegram chat IDs (private chat or group) |

**Access control is fail-closed.** The bot refuses to start if any required address or either allowlist is absent. Every command requires **both** the sender's Telegram user ID **and** the chat ID to match the configured allowlists. A group may have a negative `-100...` chat ID. Names and `@usernames` are not accepted as permissions.

The example addresses in `.env.example` use the reserved documentation range **192.0.2.0/24** and must be replaced with your environment's internal addresses. `.env` is ignored by Git.

### Local run

~~~bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python bot.py
~~~

The dependency versions in `requirements.txt` are pinned. Confirm Python compatibility in your deployment and use a staging environment before switching the production bot.

## systemd deployment

The bundled [noc-bot.service](noc-bot.service) template uses a **dedicated unprivileged account**, environment file and Linux service sandboxing. It retains the former deployment paths `/opt/noc-ai/venv/bin/python` and `/opt/noc-ai/app/bot.py` so installations can migrate deliberately; update them if your filesystem differs.

Example initial preparation:

~~~bash
sudo useradd --system --user-group --home-dir /nonexistent --shell /usr/sbin/nologin dns-noc-bot
sudo install -d -o root -g dns-noc-bot -m 0750 /etc/dns-noc-bot
# First fill your local .env with correct values, token and allowlist IDs.
sudo install -o root -g dns-noc-bot -m 0640 .env /etc/dns-noc-bot/dns-noc-bot.env
sudo install -o root -g root -m 0644 noc-bot.service /etc/systemd/system/noc-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now noc-bot.service
sudo systemctl status noc-bot.service --no-pager
~~~

If `dns-noc-bot` already exists, do not run `useradd` again. The app directory and venv must be **readable and executable** by this user. The environment file contains a token and must not be world-readable. Do not change the working production unit before these prerequisites are satisfied.

**Important:** GitHub changes do **not** update your already-running server. Deploy and validate the new code/configuration separately. No server was modified as part of this repository update.

## Security considerations

- All bot commands are guarded by a **user ID + chat ID allowlist**; this is basic access control, **not** a full authorization audit.
- The bot runs without root when installed with the new service template.
- It needs read access to the Prometheus API only; restrict that API by network policy.
- Logs and generated reports can still contain internal infrastructure identifiers; share them with authorized staff only.
- Additional hardening may include rate limiting, structured API-error handling, dependency CVE scanning and tests.
- Older commits of this **public** repository contained internal host addresses. Moving them to an environment file in the latest commit **does not erase Git history**. Review disclosure and rotate any actual credentials if they were ever committed.

## Context

Part of a broader infrastructure effort: deployed **OpenStack Kolla-Ansible Multinode** for a mobile network operator, ran two Unbound DNS resolvers, built DNS/host metrics and Grafana dashboards, added NOC tooling, and later migrated the DNS workloads to Proxmox VE.

[**Read the Cloud & DNS infrastructure case study →**](https://github.com/codexhtb/codexhtb/blob/main/projects/private-cloud-dns-observability.md)
