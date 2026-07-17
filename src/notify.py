"""Envia o resumo do dia para Slack e/ou Microsoft Teams via webhook.

Configure por variável de ambiente (GitHub Secrets):
  - SLACK_WEBHOOK_URL   (Incoming Webhook do Slack)
  - TEAMS_WEBHOOK_URL   (Incoming Webhook do Teams)
  - DASHBOARD_URL       (link do GitHub Pages, ex.: https://org.github.io/news_ia/)
"""
import os

import httpx

TIMEOUT = 15.0


def _top_bullets(digest: dict, limit: int = 4) -> list[str]:
    bullets = list(digest.get("tldr", []))
    if bullets:
        return bullets[:limit]
    # fallback: pega os itens de maior relevância
    items = [it for th in digest.get("themes", []) for it in th.get("items", [])]
    items.sort(key=lambda x: x.get("relevance", 0), reverse=True)
    return [f"{it.get('title')} ({it.get('source')})" for it in items[:limit]]


def notify_slack(digest: dict, dashboard_url: str) -> None:
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        return
    bullets = "\n".join(f"• {b}" for b in _top_bullets(digest))
    text = (
        f"*🛰️ Radar de IA — {digest.get('date', '')}*\n\n{bullets}\n\n"
        f"<{dashboard_url}|Ver compilado completo no dashboard →>"
    )
    try:
        r = httpx.post(url, json={"text": text}, timeout=TIMEOUT)
        r.raise_for_status()
        print("[notify] Slack enviado")
    except Exception as exc:  # noqa: BLE001
        print(f"[notify] falha no Slack: {exc}")


def notify_teams(digest: dict, dashboard_url: str) -> None:
    """Envia um Adaptive Card compatível com o Teams via Power Automate (Workflows).

    Os antigos "Incoming Webhook" (Office 365 Connectors) foram descontinuados
    pela Microsoft. O webhook deve vir de um fluxo do Power Automate criado com
    o gatilho "Quando uma solicitação de webhook do Teams é recebida" + a ação
    "Postar mensagem em um chat ou canal".

    O corpo enviado é {"text": "<html>"}; no campo Mensagem do fluxo, referencie
    esse conteúdo com a expressão:  triggerBody()?['text']
    """
    url = os.environ.get("TEAMS_WEBHOOK_URL")
    if not url:
        return
    bullets = "".join(f"<li>{b}</li>" for b in _top_bullets(digest))
    html = (
        f"<h3>🛰️ Radar de IA — {digest.get('date', '')}</h3>"
        f"<b>TL;DR da semana</b><ul>{bullets}</ul>"
    )
    if dashboard_url:
        html += f'<p><a href="{dashboard_url}">Ver compilado completo no dashboard →</a></p>'

    try:
        r = httpx.post(url, json={"text": html}, timeout=TIMEOUT)
        r.raise_for_status()
        print("[notify] Teams enviado")
    except Exception as exc:  # noqa: BLE001
        print(f"[notify] falha no Teams: {exc}")


def notify_all(digest: dict) -> None:
    dashboard_url = os.environ.get("DASHBOARD_URL", "")
    notify_slack(digest, dashboard_url)
    notify_teams(digest, dashboard_url)
