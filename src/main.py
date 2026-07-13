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

    # 1) Coletar
    raw = collect.collect_all(sources, lookback)

    # 2) Deduplicar (remove o que já foi visto em dias anteriores)
    new_items = store.filter_new(raw)
    print(f"[main] {len(new_items)} itens novos após dedup")

    # 3) Resumir/rankear com Claude
    digest = summarize.synthesize(
        new_items,
        team_context=settings.get("team_context", ""),
        model=settings["models"]["synthesis"],
        max_items=settings.get("max_items_to_synthesize", 60),
    )
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    digest["date"] = date_str
    digest["item_count"] = len(new_items)

    # 4) Persistir + renderizar dashboard
    store.save_digest(date_str, digest)
    render.build_dashboard(settings.get("dashboard_title", "Radar de IA"))

    # 5) Notificar canais
    if args.dry_run:
        print("[main] dry-run: pulando notificações")
    else:
        notify.notify_all(digest)

    print(f"[main] concluído para {date_str} ({len(new_items)} itens)")


if __name__ == "__main__":
    main()
