# DNS NOC Bot

**Python · Telegram Bot API · Prometheus · DNS & Linux Infrastructure Monitoring**

A lightweight **read-only NOC command interface** for a two-resolver Unbound DNS environment. Engineers can request a quick operational summary, examine DNS errors and cache efficiency, compare resolvers, inspect conntrack, or generate a short QPS graph — without opening a full Grafana dashboard for every check.

[← Cloud & DNS infrastructure engineering case](https://github.com/codexhtb/codexhtb/blob/main/projects/private-cloud-dns-observability.md) · [Pulse DNS observability](https://github.com/codexhtb/pulse)

> **Repository status: internal automation prototype/reference implementation, not a hardened public bot service.** The currently published code contains environment-specific private host addresses, does not enforce a Telegram user/chat allowlist, and ships a root-run systemd service example. Review and remediate these limitations before using it with production monitoring.

## Features visible in the source

| Command | What it returns |
| --- | --- |
| \`/status dns1\` / \`/status dns2\` | Resolver QPS, 24-hour peak, SERVFAIL, NXDOMAIN, cache hit ratio, CPU, memory, conntrack |
| \`/status_dns1\` / \`/status_dns2\` | Shortcuts for per-resolver status |
| \`/health\` | Aggregated resolver report, traffic split and an imbalance warning |
| \`/alerts\` | Currently firing Prometheus alerts and severities |
| \`/compare\` | DNS1 vs DNS2 QPS |
| \`/summary\` | Combined QPS and active-alert count |
| \`/analyze dns1\` | Resolver load estimate, failures, cache effectiveness |
| \`/conntrack\` | Conntrack use/limit and threshold warnings |
| \`/graph dns1\` / \`/graph dns2\` | Six-hour resolver QPS plots generated with Matplotlib |
| \`/overlay\` | Comparative DNS QPS plot |

The bot uses the **Prometheus HTTP API**: instant vector queries for operational summaries and range queries for charts. It does **not** modify Unbound, firewall rules, or alerts.

## Architecture

~~~mermaid
flowchart LR
    DNS1["Unbound DNS1 metrics"] --> P["Prometheus"]
    DNS2["Unbound DNS2 metrics"] --> P
    NODE["Linux/node exporter metrics"] --> P
    P --> G["Grafana dashboards"]
    P --> B["Python DNS NOC Bot"]
    B --> T["Telegram NOC commands"]
~~~

## Technical notes

- **Main implementation:** [bot.py](bot.py) — Telegram command handlers and Prometheus queries.
- **Environment template:** [.env.example](.env.example) defines \`BOT_TOKEN\` and \`PROM_URL\`.
- **Service example:** [noc-bot.service](noc-bot.service) is environment-specific and **must not be copied to production as-is**.
- **Dependencies:** the present \`requirements.txt\` is empty; the code imports \`python-telegram-bot\`, \`requests\`, \`python-dotenv\`, and \`matplotlib\`. Pin and test compatible versions before deployment.
- **Host discovery:** \`HOST_MAP\` is currently hard-coded in the Python source; do not treat the example as a portable configuration.

## Security work required before production use

1. Enforce a **Telegram user/chat allowlist** and verify every command request server-side.
2. Move host mappings and internal URLs out of the source code into protected configuration.
3. Use a dedicated **unprivileged systemd service account**; do not run the bot as root.
4. Restrict network access to the Prometheus API and protect the bot token.
5. Add pinned dependencies, structured error handling, rate limits, and tests.
6. Review Git history for private infrastructure information if the repository is to remain public.

## Context

This bot is one component of a larger DNS operations effort: a production **OpenStack Kolla-Ansible Multinode** environment, two **Unbound resolvers** for a mobile network operator, custom Prometheus DNS metrics, Grafana dashboards and alerting, followed by a migration of DNS workloads to **Proxmox VE**.

Read the **[complete cloud & DNS engineering case study](https://github.com/codexhtb/codexhtb/blob/main/projects/private-cloud-dns-observability.md)** for the larger context.

---

*No live monitoring credentials or operator subscriber data are intentionally documented in this README.*
