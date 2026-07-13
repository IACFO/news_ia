"""Gera o dashboard web (GitHub Pages) e o Markdown do dia."""
import html
from pathlib import Path

from store import load_all_digests

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

# Identidade visual Grupo Casas Bahia
CSS = """
:root{
  --gcb-azul:#0033C6; --gcb-vermelho:#E31233; --gcb-off-white:#F0EFEA;
  --gcb-preto:#231F20; --gcb-branco:#FCFCFC; --gcb-cinza:#53585F;
  --font-display:'Urbanist','Helvetica Neue',Arial,sans-serif;
  --font-body:'Roboto','Helvetica Neue',Arial,sans-serif;
  --radius-card:16px; --radius-button:999px;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font-body);background:var(--gcb-off-white);color:var(--gcb-preto);line-height:1.55}
header{background:var(--gcb-azul);color:var(--gcb-branco);padding:28px 24px}
header h1{font-family:var(--font-display);font-weight:900;font-size:1.7rem}
header p{opacity:.85;margin-top:4px;font-size:.95rem}
.wrap{display:flex;max-width:1100px;margin:0 auto;gap:24px;padding:24px}
main{flex:1;min-width:0}
aside{width:220px;flex-shrink:0}
aside h3{font-family:var(--font-display);font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;color:var(--gcb-cinza);margin-bottom:10px}
aside a{display:block;padding:8px 12px;border-radius:var(--radius-button);color:var(--gcb-preto);text-decoration:none;font-size:.9rem;margin-bottom:4px}
aside a:hover{background:#fff}
aside a.active{background:var(--gcb-azul);color:var(--gcb-branco);font-weight:700}
.tldr{background:var(--gcb-azul);color:var(--gcb-branco);border-radius:var(--radius-card);padding:20px 24px;margin-bottom:28px}
.tldr h2{font-family:var(--font-display);font-weight:700;font-size:1rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px}
.tldr ul{list-style:none} .tldr li{padding:5px 0 5px 22px;position:relative}
.tldr li::before{content:'▸';position:absolute;left:0;color:var(--gcb-vermelho);font-weight:700}
.theme{margin-bottom:32px}
.theme > h2{font-family:var(--font-display);font-weight:900;font-size:1.25rem;color:var(--gcb-azul);border-bottom:3px solid var(--gcb-vermelho);display:inline-block;padding-bottom:4px;margin-bottom:16px}
.card{background:var(--gcb-branco);border-radius:var(--radius-card);padding:18px 20px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.card h3{font-family:var(--font-display);font-weight:700;font-size:1.05rem;margin-bottom:6px}
.card h3 a{color:var(--gcb-preto);text-decoration:none}
.card h3 a:hover{color:var(--gcb-azul)}
.card p{font-size:.92rem;margin-bottom:6px}
.card .why{color:var(--gcb-cinza);font-size:.85rem;font-style:italic}
.meta{display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap}
.badge{font-size:.72rem;font-weight:700;padding:3px 10px;border-radius:var(--radius-button);background:var(--gcb-off-white);color:var(--gcb-cinza)}
.rel{font-size:.72rem;font-weight:700;padding:3px 10px;border-radius:var(--radius-button);color:#fff;background:var(--gcb-cinza)}
.rel-5,.rel-4{background:var(--gcb-vermelho)} .rel-3{background:var(--gcb-azul)}
footer{text-align:center;padding:24px;color:var(--gcb-cinza);font-size:.8rem}
@media(max-width:760px){.wrap{flex-direction:column}aside{width:100%}}
"""

HEAD = """<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Urbanist:wght@400;500;700;900&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
"""


def _esc(s) -> str:
    return html.escape(str(s or ""))


def _render_items(items: list[dict]) -> str:
    out = []
    for it in items:
        rel = int(it.get("relevance", 3) or 3)
        url = _esc(it.get("url"))
        title = _esc(it.get("title"))
        title_html = f'<a href="{url}" target="_blank" rel="noopener">{title}</a>' if url else title
        why = f'<p class="why">Por que importa: {_esc(it["why"])}</p>' if it.get("why") else ""
        out.append(
            f'<div class="card"><h3>{title_html}</h3>'
            f'<p>{_esc(it.get("summary"))}</p>{why}'
            f'<div class="meta"><span class="badge">{_esc(it.get("source"))}</span>'
            f'<span class="rel rel-{rel}">Relevância {rel}/5</span></div></div>'
        )
    return "\n".join(out)


def _render_page(digest: dict, all_dates: list[str], active: str, title: str) -> str:
    tldr_items = "".join(f"<li>{_esc(b)}</li>" for b in digest.get("tldr", []))
    themes_html = []
    for theme in digest.get("themes", []):
        themes_html.append(
            f'<section class="theme"><h2>{_esc(theme.get("name"))}</h2>'
            f'{_render_items(theme.get("items", []))}</section>'
        )
    date_label = digest.get("date", active)
    return f"""<!doctype html><html lang="pt-br"><head>{HEAD}
<title>{_esc(title)} — {_esc(date_label)}</title><style>{CSS}</style></head><body>
<header><h1>{_esc(title)}</h1><p>Compilado diário de novidades de IA · {_esc(date_label)}</p></header>
<div class="wrap">
<main>
<div class="tldr"><h2>TL;DR do dia</h2><ul>{tldr_items}</ul></div>
{''.join(themes_html)}
</main>
<aside><h3>Histórico</h3>{{NAV}}</aside>
</div>
<footer>Radar de IA · Grupo Casas Bahia · gerado automaticamente</footer>
</body></html>"""


def build_dashboard(title: str) -> None:
    digests = load_all_digests()
    if not digests:
        print("[render] sem digests para renderizar")
        return
    dates = [d.get("date", "") for d in digests]
    (DOCS_DIR / "day").mkdir(parents=True, exist_ok=True)

    for i, digest in enumerate(digests):
        active = dates[i]
        is_latest = i == 0
        prefix = "" if is_latest else "../"
        nav_links = []
        for j, d in enumerate(dates):
            cls = "active" if d == active else ""
            href = f"{prefix}index.html" if j == 0 else f"{prefix}day/{d}.html"
            nav_links.append(f'<a class="{cls}" href="{href}">{_esc(d)}</a>')
        page = _render_page(digest, dates, active, title).replace("{NAV}", "".join(nav_links))
        target = DOCS_DIR / "index.html" if is_latest else DOCS_DIR / "day" / f"{active}.html"
        target.write_text(page, encoding="utf-8")
    print(f"[render] dashboard gerado com {len(digests)} dias em {DOCS_DIR}")


def to_markdown(digest: dict) -> str:
    """Versão Markdown do digest (útil para arquivar ou colar em outros canais)."""
    lines = [f"# Radar de IA — {digest.get('date', '')}", "", "## TL;DR"]
    lines += [f"- {b}" for b in digest.get("tldr", [])]
    for theme in digest.get("themes", []):
        lines += ["", f"## {theme.get('name')}"]
        for it in theme.get("items", []):
            rel = it.get("relevance", 3)
            url = it.get("url", "")
            title = f"[{it.get('title')}]({url})" if url else it.get("title")
            lines.append(f"- **{title}** _(relevância {rel}/5 · {it.get('source')})_")
            lines.append(f"  - {it.get('summary')}")
            if it.get("why"):
                lines.append(f"  - _Por que importa:_ {it['why']}")
    return "\n".join(lines)
