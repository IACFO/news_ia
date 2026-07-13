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


def filter_new(items: list[dict]) -> list[dict]:
    """Devolve só os itens que ainda não tinham sido vistos e os marca como vistos."""
    conn = connect()
    now = datetime.now(timezone.utc).isoformat()
    new_items = []
    for item in items:
        iid = _item_id(item)
        row = conn.execute("SELECT 1 FROM seen WHERE id = ?", (iid,)).fetchone()
        if row:
            continue
        conn.execute(
            "INSERT OR IGNORE INTO seen (id, url, title, first_seen) VALUES (?, ?, ?, ?)",
            (iid, item.get("url"), item.get("title"), now),
        )
        new_items.append(item)
    conn.commit()
    conn.close()
    return new_items


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
