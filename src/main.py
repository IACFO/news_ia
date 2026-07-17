"""Orquestra o pipeline: coleta -> dedup -> resume -> renderiza -> notifica.

Uso:
  python src/main.py            # roda o pipeline do dia
  python src/main.py --dry-run  # coleta e resume, mas não notifica canais
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import collect  # noqa: E402
import notify  # noqa: E402
import render  # noqa: E402
import store  # noqa: E402
import summarize  # noqa: E402

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_yaml(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="não envia para Slack/Teams")
    args = ap.parse_args()

    sources = load_yaml("sources.yaml")
    settings = load_yaml("settings.yaml")
    lookback = settings.get("lookback_hours", 30)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1) Coletar
    raw = collect.collect_all(sources, lookback)

    # 2) Filtrar o que já foi visto (SEM marcar ainda — só leitura)
    new_items = store.filter_unseen(raw)
    print(f"[main] {len(new_items)} itens novos após dedup")

    # 2b) Sem itens novos: não sobrescreve um digest bom já existente do dia.
    if not new_items:
        existing = store.load_digest(date_str)
        if existing and existing.get("themes"):
            print("[main] sem itens novos; mantendo o digest existente de hoje")
            render.build_dashboard(settings.get("dashboard_title", "Radar de IA"))
            return
        digest = {"tldr": ["Nenhuma novidade relevante coletada nesta semana."], "themes": []}
        digest.update(date=date_str, item_count=0)
        store.save_digest(date_str, digest)
        render.build_dashboard(settings.get("dashboard_title", "Radar de IA"))
        print("[main] concluído: nenhum item novo hoje")
        return

    # 3) Resumir/rankear com o Gemini
    digest, ok = summarize.synthesize(
        new_items,
        team_context=settings.get("team_context", ""),
        model=settings["models"]["synthesis"],
        max_items=settings.get("max_items_to_synthesize", 60),
    )
    digest["date"] = date_str
    digest["item_count"] = len(new_items)

    # 4) Persistir + renderizar dashboard
    store.save_digest(date_str, digest)
    render.build_dashboard(settings.get("dashboard_title", "Radar de IA"))

    # 5) Só marca como visto se a síntese deu certo (senão, permite nova tentativa)
    if ok:
        store.mark_seen(new_items)
    else:
        print("[main] síntese falhou; itens NÃO marcados como vistos (retry possível)")

    # 6) Notificar canais (só quando o digest é bom)
    if args.dry_run:
        print("[main] dry-run: pulando notificações")
    elif ok:
        notify.notify_all(digest)

    print(f"[main] concluído para {date_str} ({len(new_items)} itens, ok={ok})")


if __name__ == "__main__":
    main()
