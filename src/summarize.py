"""Usa a Claude API para agrupar, resumir e pontuar relevância dos itens."""
import json
import os

from anthropic import Anthropic

SYSTEM_PROMPT = """Você é o analista do radar de IA de um time de engenharia.
Recebe uma lista de itens de notícias/papers sobre IA coletados hoje e devolve um
compilado consolidado, em português do Brasil, com tom direto e sem jargão.

Sua tarefa:
1. Descartar ruído, duplicatas e o que for irrelevante para o contexto do time.
2. Agrupar o que sobrar em TEMAS (ex.: "Novos modelos", "Agentes e MCP",
   "Performance e custo", "Ferramentas", "Papers", "Varejo/negócio").
3. Para cada item mantido, escrever um resumo de 1-2 frases e uma nota de
   relevância de 1 a 5 para ESTE time (5 = impacto direto nos projetos deles).
4. Escrever um "TL;DR" de 2-4 bullets com o mais importante do dia.

Responda APENAS com JSON válido, sem texto ao redor, neste formato:
{
  "tldr": ["bullet 1", "bullet 2"],
  "themes": [
    {
      "name": "Nome do tema",
      "items": [
        {
          "title": "Título curto e claro",
          "summary": "Resumo de 1-2 frases.",
          "why": "Por que importa para o time (1 frase).",
          "relevance": 4,
          "source": "Fonte",
          "url": "https://..."
        }
      ]
    }
  ]
}
Ordene os temas e os itens dentro de cada tema por relevância (maior primeiro)."""


def synthesize(items: list[dict], team_context: str, model: str, max_items: int) -> dict:
    """Chama Claude e devolve o digest estruturado. Faz fallback se algo falhar."""
    if not items:
        return {"tldr": ["Nenhuma novidade relevante coletada hoje."], "themes": []}

    items = items[:max_items]
    payload = [
        {
            "title": it.get("title", ""),
            "summary": it.get("summary", ""),
            "source": it.get("source", ""),
            "tag": it.get("tag", ""),
            "url": it.get("url", ""),
        }
        for it in items
    ]

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    user_msg = (
        f"CONTEXTO DO TIME:\n{team_context}\n\n"
        f"ITENS COLETADOS HOJE ({len(payload)}):\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    resp = client.messages.create(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text").strip()

    # Claude às vezes embrulha em ```json ... ``` — limpa antes de parsear.
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip("` \n")

    try:
        digest = json.loads(text)
    except json.JSONDecodeError:
        print("[summarize] resposta não veio em JSON; usando fallback bruto.")
        digest = {
            "tldr": ["A IA não conseguiu estruturar o digest hoje. Itens brutos abaixo."],
            "themes": [
                {
                    "name": "Itens coletados",
                    "items": [
                        {
                            "title": it["title"],
                            "summary": it.get("summary", "")[:200],
                            "why": "",
                            "relevance": 3,
                            "source": it.get("source", ""),
                            "url": it.get("url", ""),
                        }
                        for it in items
                    ],
                }
            ],
        }
    return digest
