import os
import requests

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PROM_URL = os.getenv("PROM_URL")

HOST_MAP = {
    "dns1": "172.24.68.20:9100",
    "dns2": "172.24.68.21:9100",
}


# -------------------------
# Prometheus helpers
# -------------------------
def prom(query: str):
    r = requests.get(
        f"{PROM_URL}/api/v1/query",
        params={"query": query},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["data"]["result"]


def val(query: str):
    r = prom(query)
    if not r:
        return 0.0
    return float(r[0]["value"][1])


def gb(bytes_val):
    return bytes_val / 1024 / 1024 / 1024


# -------------------------
# STATUS
# -------------------------
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /status dns1|dns2"
        )
        return

    host = context.args[0]

    if host not in HOST_MAP:
        await update.message.reply_text(
            "Unknown host"
        )
        return

    node = HOST_MAP[host]

    qps = val(
        f'unbound:qps:15s{{instance="{host}"}}'
    )

    peak = val(
        f'max_over_time(unbound:qps:15s{{instance="{host}"}}[24h])'
    )

    servfail_rps = val(
        f'unbound:servfail:5m{{instance="{host}"}}'
    )

    nxdomain_rps = val(
        f'unbound:nxdomain:5m{{instance="{host}"}}'
    )

    cache = val(
        f'unbound:cache_hit_ratio:5m{{instance="{host}"}}'
    )

    cpu = val(
        f'100-(avg by(instance)(rate(node_cpu_seconds_total{{instance="{node}",mode="idle"}}[5m]))*100)'
    )

    ram = val(
        f'node_memory_MemAvailable_bytes{{instance="{node}"}}'
    )

    servfail_pct = (
        servfail_rps / qps * 100
        if qps > 0 else 0
    )

    nxdomain_pct = (
        nxdomain_rps / qps * 100
        if qps > 0 else 0
    )

    msg = (
        f"DNS {host}\n\n"
        f"QPS: {qps:.0f}\n"
        f"Peak24h: {peak:.0f}\n\n"
        f"CPU: {cpu:.2f}%\n"
        f"RAM free: {gb(ram):.1f} GB\n\n"
        f"SERVFAIL: {servfail_rps:.2f} req/s ({servfail_pct:.2f}%)\n"
        f"NXDOMAIN: {nxdomain_rps:.2f} req/s ({nxdomain_pct:.2f}%)\n"
        f"Cache: {cache * 100:.2f}%"
    )

    await update.message.reply_text(msg)


async def status_dns1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.args = ["dns1"]
    await status(update, context)


async def status_dns2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.args = ["dns2"]
    await status(update, context)


# -------------------------
# HEALTH
# -------------------------
async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rows = []
    total_qps = 0

    for host, node in HOST_MAP.items():

        qps = val(
            f'unbound:qps:15s{{instance="{host}"}}'
        )

        peak = val(
            f'max_over_time(unbound:qps:15s{{instance="{host}"}}[24h])'
        )

        servfail = val(
            f'unbound:servfail:5m{{instance="{host}"}}'
        )

        nxdomain = val(
            f'unbound:nxdomain:5m{{instance="{host}"}}'
        )

        cache = val(
            f'unbound:cache_hit_ratio:5m{{instance="{host}"}}'
        )

        cpu = val(
            f'100-(avg by(instance)(rate(node_cpu_seconds_total{{instance="{node}",mode="idle"}}[5m]))*100)'
        )

        ram = val(
            f'node_memory_MemAvailable_bytes{{instance="{node}"}}'
        )

        total_qps += qps

        rows.append({
            "host": host,
            "qps": qps,
            "peak": peak,
            "servfail": servfail,
            "nxdomain": nxdomain,
            "cache": cache,
            "cpu": cpu,
            "ram": ram,
        })

    msg = "🟢 DNS CLUSTER HEALTH\n\n"

    for r in rows:

        msg += (
            f"{r['host']}\n"
            f"QPS: {r['qps']:.0f}\n"
            f"Peak24h: {r['peak']:.0f}\n"
            f"CPU: {r['cpu']:.2f}%\n"
            f"RAM free: {gb(r['ram']):.1f} GB\n"
            f"SERVFAIL: {r['servfail']:.2f} req/s\n"
            f"NXDOMAIN: {r['nxdomain']:.2f} req/s\n"
            f"Cache: {r['cache'] * 100:.2f}%\n\n"
        )

    if total_qps > 0:

        dns1_share = rows[0]["qps"] / total_qps * 100
        dns2_share = rows[1]["qps"] / total_qps * 100

        msg += (
            "LOAD SPLIT\n"
            f"dns1: {dns1_share:.1f}%\n"
            f"dns2: {dns2_share:.1f}%\n"
        )

        if dns1_share > 75 or dns2_share > 75:
            msg += "\n\n⚠️ Load imbalance detected"

    await update.message.reply_text(msg)


# -------------------------
# ALERTS
# -------------------------
async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):

    data = prom('ALERTS{alertstate="firing"}')

    if not data:
        await update.message.reply_text(
            "🟢 No active alerts"
        )
        return

    msg = "🔴 ACTIVE ALERTS\n\n"

    for a in data:

        labels = a["metric"]

        msg += (
            f"{labels.get('alertname', 'unknown')}\n"
            f"Instance: {labels.get('instance', '-')}\n"
            f"Severity: {labels.get('severity', '-')}\n\n"
        )

    await update.message.reply_text(msg)


# -------------------------
# COMPARE
# -------------------------
async def compare(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dns1 = val('unbound:qps:15s{instance="dns1"}')
    dns2 = val('unbound:qps:15s{instance="dns2"}')

    msg = (
        "📊 DNS COMPARE\n\n"
        f"dns1: {dns1:.0f} qps\n"
        f"dns2: {dns2:.0f} qps\n\n"
        f"Difference: {abs(dns1 - dns2):.0f} qps"
    )

    await update.message.reply_text(msg)


# -------------------------
# SUMMARY
# -------------------------
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dns1 = val('unbound:qps:15s{instance="dns1"}')
    dns2 = val('unbound:qps:15s{instance="dns2"}')

    total = dns1 + dns2

    active_alerts = prom(
        'ALERTS{alertstate="firing"}'
    )

    msg = (
        "📊 NOC SUMMARY\n\n"
        f"Traffic: {total:.0f} QPS\n"
        f"Active alerts: {len(active_alerts)}\n\n"
    )

    if total > 0:
        msg += (
            f"dns1: {dns1 / total * 100:.1f}%\n"
            f"dns2: {dns2 / total * 100:.1f}%\n"
        )

    if not active_alerts:
        msg += "\n🟢 System healthy"

    await update.message.reply_text(msg)


# -------------------------
# MAIN
# -------------------------
def main():

    app = ApplicationBuilder().token(
        BOT_TOKEN
    ).build()

    app.add_handler(
        CommandHandler("status", status)
    )

    app.add_handler(
        CommandHandler("status_dns1", status_dns1)
    )

    app.add_handler(
        CommandHandler("status_dns2", status_dns2)
    )

    app.add_handler(
        CommandHandler("health", health)
    )

    app.add_handler(
        CommandHandler("alerts", alerts)
    )

    app.add_handler(
        CommandHandler("compare", compare)
    )

    app.add_handler(
        CommandHandler("summary", summary)
    )

    app.run_polling()


if __name__ == "__main__":
    main()
