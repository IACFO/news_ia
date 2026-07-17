"""Usa a API do Gemini (Google AI Studio) para agrupar, resumir e pontuar itens."""
import json
import os

from google import genai
from google.genai import types

SYSTEM_PROMPT = """Você é o analista do radar de IA de um time de engenharia.
Recebe uma lista de itens de notícias/papers sobre IA coletados na semana e devolve um
compilado consolidado, em português do Brasil, com tom direto e sem jargão.

Sua tarefa:
1. Descartar ruído, duplicatas e o que for irrelevante para o contexto do time.
2. Agrupar o que sobrar em TEMAS (ex.: "Novos modelos", "Agentes e MCP",
   "Performance e custo", "Ferramentas", "Papers", "Varejo/negócio").
3. Para cada item mantido, escrever um resumo de 1-2 frases e uma nota de
   relevância de 1 a 5 para ESTE time (5 = impacto direto nos projetos deles).
4. Escrever um "TL;DR" de 3-5 bullets com o mais importante da semana.

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


def synthesize(
    items: list[dict], team_context: str, model: str, max_items: int
) -> tuple[dict, bool]:
    """Chama o Gemini e devolve (digest, ok). ok=False em falha/fallback — o main
    usa isso para NÃO marcar os itens como vistos, permitindo nova tentativa."""
    if not items:
        return {"tldr": ["Nenhuma novidade relevante coletada nesta semana."], "themes": []}, False

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

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    user_msg = (
        f"CONTEXTO DO TIME:\n{team_context}\n\n"
        f"ITENS COLETADOS NESTA SEMANA ({len(payload)}):\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    resp = client.models.generate_content(
        model=model,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",  # força JSON puro, sem ```
            max_output_tokens=16000,
            temperature=0.3,
            # gemini-2.5-flash "pensa" por padrão e gasta tokens de saída nisso,
            # o que cortava o JSON. Desligamos: a tarefa não precisa de raciocínio.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    text = (resp.text or "").strip()

    # Segurança: se ainda vier embrulhado em ```json ... ```, limpa antes de parsear.
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip("` \n")

    try:
        digest = json.loads(text)
    except json.JSONDecodeError:
        # Diagnóstico: por que falhou? (motivo de parada + trecho da resposta)
        try:
            finish = resp.candidates[0].finish_reason
        except Exception:  # noqa: BLE001
            finish = "?"
        print(f"[summarize] JSON inválido (finish_reason={finish}); usando fallback bruto.")
        print(f"[summarize] início da resposta: {text[:300]!r}")
        digest = {
            "tldr": ["A IA não conseguiu estruturar o digest desta semana. Itens brutos abaixo."],
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
        return digest, False  # fallback: não marca como visto, permite retry
    return digest, True
