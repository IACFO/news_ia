# 🛰️ Radar de IA — Grupo Casas Bahia

Bot que varre fontes confiáveis de IA (labs, papers, newsletters, mídia, comunidade)
e gera um **compilado diário** consolidado para o time de IA: lançamentos, modelos,
performance, agentes, MCP, ferramentas e casos de uso.

Entrega em dois canais:
- **Teams / Slack** — mensagem com o TL;DR do dia + link.
- **Dashboard web** (GitHub Pages) — compilado completo, com histórico consultável.

Roda sozinho todo dia útil via **GitHub Actions**.

## Como funciona

```
[coleta] → [dedup] → [resume+rankeia (Claude)] → [dashboard + notifica canais]
```

| Etapa | Arquivo |
|---|---|
| Coleta (RSS, arXiv, Hacker News) | [src/collect.py](src/collect.py) |
| Memória / deduplicação (SQLite) | [src/store.py](src/store.py) |
| Síntese e ranking com Claude | [src/summarize.py](src/summarize.py) |
| Dashboard web (identidade GCB) | [src/render.py](src/render.py) |
| Envio Teams/Slack | [src/notify.py](src/notify.py) |
| Orquestração | [src/main.py](src/main.py) |

As fontes ficam em [config/sources.yaml](config/sources.yaml) e o comportamento
(contexto do time, modelos, janela de coleta) em [config/settings.yaml](config/settings.yaml).

## Rodar localmente

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...                  # Windows: $env:ANTHROPIC_API_KEY="..."
python src/main.py --dry-run                         # coleta e resume, sem notificar
```

Abra `docs/index.html` no navegador para ver o dashboard gerado.

## Colocar no ar (produção)

1. Suba este projeto para um repositório no GitHub.
2. Em **Settings → Secrets and variables → Actions**, cadastre:
   - Secret `ANTHROPIC_API_KEY`
   - Secret `TEAMS_WEBHOOK_URL` e/ou `SLACK_WEBHOOK_URL` (Incoming Webhook do canal)
   - Variable `DASHBOARD_URL` (o link do GitHub Pages, ex.: `https://SUA-ORG.github.io/news_ia/`)
3. Em **Settings → Pages**, selecione *GitHub Actions* como source.
4. Pronto — o workflow [daily.yml](.github/workflows/daily.yml) roda 09h (BRT) em dias úteis.
   Dá para rodar na hora pela aba **Actions → Run workflow**.

## Próximos passos (roadmap)

- Adicionar X/Twitter e Reddit como fontes.
- Feedback loop: o time marca o que foi útil → ajusta o ranking.
- Triagem em massa com modelo mais barato antes da síntese (reduz custo).
