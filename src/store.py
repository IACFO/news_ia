"""Memória do bot: guarda o que já foi visto (dedup) e o histórico de digests."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "seen.db"
DIGEST_DIR = DATA_DIR / "digests"


def _item_id(item: dict) -> str:
    """ID estável de um item, baseado na URL (ou título se não houver URL)."""
    key = (item.get("url") or item.get("title") or "").strip().lower()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen (
            id TEXT PRIMARY KEY,
            url TEXT,
            title TEXT,
            first_seen TEXT
        )
        """
    )
    conn.commit()
    return conn


def filter_unseen(items: list[dict]) -> list[dict]:
    """Devolve só os itens ainda não vistos — SEM marcá-los (somente leitura).

    A marcação fica para mark_seen(), chamado apenas após um resumo bem-sucedido,
    para que uma falha de síntese não "queime" os itens.
    """
    conn = connect()
    unseen = []
    for item in items:
        row = conn.execute("SELECT 1 FROM seen WHERE id = ?", (_item_id(item),)).fetchone()
        if not row:
            unseen.append(item)
    conn.close()
    return unseen


def mark_seen(items: list[dict]) -> None:
    """Marca itens como vistos. Chamar só depois de salvar um digest bom."""
    conn = connect()
    now = datetime.now(timezone.utc).isoformat()
    for item in items:
        conn.execute(
            "INSERT OR IGNORE INTO seen (id, url, title, first_seen) VALUES (?, ?, ?, ?)",
            (_item_id(item), item.get("url"), item.get("title"), now),
        )
    conn.commit()
    conn.close()


def load_digest(date_str: str) -> dict | None:
    """Carrega o digest de um dia específico, se existir."""
    path = DIGEST_DIR / f"{date_str}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def save_digest(date_str: str, digest: dict) -> Path:
    """Salva o digest do dia como JSON (fonte de verdade para o dashboard)."""
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    path = DIGEST_DIR / f"{date_str}.json"
    path.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_all_digests() -> list[dict]:
    """Carrega todos os digests salvos, do mais recente para o mais antigo."""
    if not DIGEST_DIR.exists():
        return []
    digests = []
    for path in sorted(DIGEST_DIR.glob("*.json"), reverse=True):
        try:
            digests.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return digests
