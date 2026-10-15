"""
Gemini API Key Rotation Manager
================================
একাধিক Gemini API key কে round-robin এ ব্যবহার করে।
429 (rate limit) error হলে সেই key কে 24 ঘন্টার জন্য cooldown এ রাখে।
Cooldown state PostgreSQL database এ persist হয়, তাই server restart এও মনে থাকে।

Usage:
    from Cnpi_RAG.utils.key_manager import get_key_manager
    
    km = get_key_manager()
    key, label = km.get_next_key()          # available key নাও
    km.mark_exhausted(key, label, "429 error msg")  # limit হলে mark করো
"""

import os
import hashlib
import threading
import logging
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ===========================================================================
# Database connection helper
# ===========================================================================

def _get_db_conn():
    """PostgreSQL connection খোলো (env থেকে credentials নাও)."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url, connect_timeout=10)
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=int(os.getenv("DB_PORT", 5432)),
        sslmode=os.getenv("DB_SSLMODE", "require"),
        connect_timeout=10,
    )


def _hash_key(api_key: str) -> str:
    """API key এর SHA256 hash বানাও (plain key DB তে রাখা safe না)."""
    return hashlib.sha256(api_key.encode()).hexdigest()


# ===========================================================================
# Table auto-creation
# ===========================================================================

_TABLE_CREATED = False
_TABLE_LOCK = threading.Lock()

def _ensure_table():
    """gemini_key_cooldown table না থাকলে তৈরি করো।"""
    global _TABLE_CREATED
    if _TABLE_CREATED:
        return
    with _TABLE_LOCK:
        if _TABLE_CREATED:
            return
        try:
            conn = _get_db_conn()
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS gemini_key_cooldown (
                            id           SERIAL PRIMARY KEY,
                            key_hash     VARCHAR(64) UNIQUE NOT NULL,
                            key_label    VARCHAR(50) NOT NULL,
                            exhausted_at TIMESTAMPTZ NOT NULL,
                            cooldown_hours INTEGER NOT NULL DEFAULT 24,
                            notes        TEXT
                        )
                    """)
                    # available_at computed column হিসেবে না রেখে view বানাই
                    # (Neon/older PG compat এর জন্য)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_gemini_cooldown_hash
                            ON gemini_key_cooldown (key_hash)
                    """)
            conn.close()
            _TABLE_CREATED = True
            logger.info("[KeyManager] gemini_key_cooldown table ready.")
        except Exception as e:
            logger.warning(f"[KeyManager] Table creation warning: {e}")
            _TABLE_CREATED = True  # retry না করতে


# ===========================================================================
# GeminiKeyManager
# ===========================================================================

class GeminiKeyManager:
    """
    Gemini API key rotation with DB-backed 24h cooldown.

    .env থেকে GEMINI_API_KEY_1, GEMINI_API_KEY_2, ... পড়ে।
    যেসব key placeholder ("your_..._here") সেগুলো skip করে।
    """

    COOLDOWN_HOURS = 24

    def __init__(self):
        self._keys: list[tuple[str, str]] = []   # [(key_value, label), ...]
        self._index = 0
        self._lock = threading.Lock()
        self._load_keys()
        _ensure_table()

    # -----------------------------------------------------------------------
    # Key loading
    # -----------------------------------------------------------------------

    def _load_keys(self):
        """env থেকে GEMINI_API_KEY_N format এ সব key লোড করো।"""
        keys = []
        i = 1
        while True:
            label = f"GEMINI_API_KEY_{i}"
            val = os.getenv(label, "").strip()
            if not val:
                break
            # placeholder value গুলো skip করো
            if val.startswith("your_") or val == "":
                i += 1
                continue
            keys.append((val, label))
            i += 1

        # fallback: পুরনো single GEMINI_API_KEY
        if not keys:
            val = os.getenv("GEMINI_API_KEY", "").strip()
            if val and not val.startswith("your_"):
                keys.append((val, "GEMINI_API_KEY"))

        self._keys = keys
        logger.info(f"[KeyManager] Loaded {len(self._keys)} Gemini API key(s): "
                    f"{[label for _, label in self._keys]}")

    # -----------------------------------------------------------------------
    # Cooldown DB operations
    # -----------------------------------------------------------------------

    def _is_exhausted(self, api_key: str) -> bool:
        """DB তে check করো — এই key কি এখনও cooldown এ আছে?"""
        try:
            conn = _get_db_conn()
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT exhausted_at, cooldown_hours
                        FROM gemini_key_cooldown
                        WHERE key_hash = %s
                    """, (_hash_key(api_key),))
                    row = cur.fetchone()
                    if row is None:
                        return False   # কোনো record নেই → available
                    exhausted_at, cooldown_hours = row
                    now = datetime.now(timezone.utc)
                    # timezone-aware করো
                    if exhausted_at.tzinfo is None:
                        exhausted_at = exhausted_at.replace(tzinfo=timezone.utc)
                    elapsed_hours = (now - exhausted_at).total_seconds() / 3600
                    return elapsed_hours < cooldown_hours
            conn.close()
        except Exception as e:
            logger.warning(f"[KeyManager] DB check failed, assuming available: {e}")
            return False

    def mark_exhausted(self, api_key: str, label: str, notes: str = "") -> None:
        """
        এই key কে exhausted হিসেবে DB তে mark করো।
        ইতিমধ্যে record থাকলে timestamp update করো (cooldown reset হবে)।
        """
        try:
            conn = _get_db_conn()
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO gemini_key_cooldown
                            (key_hash, key_label, exhausted_at, cooldown_hours, notes)
                        VALUES (%s, %s, NOW(), %s, %s)
                        ON CONFLICT (key_hash) DO UPDATE SET
                            exhausted_at   = EXCLUDED.exhausted_at,
                            cooldown_hours = EXCLUDED.cooldown_hours,
                            notes          = EXCLUDED.notes
                    """, (_hash_key(api_key), label, self.COOLDOWN_HOURS, notes[:500] if notes else None))
            conn.close()
            logger.warning(
                f"[KeyManager] {label} marked exhausted — "
                f"cooldown {self.COOLDOWN_HOURS}h. Notes: {notes[:100]}"
            )
        except Exception as e:
            logger.error(f"[KeyManager] Failed to mark exhausted in DB: {e}")

    def get_hours_remaining(self, api_key: str) -> float:
        """এই key আর কত ঘন্টা পর available হবে (0.0 মানে এখনই available)।"""
        try:
            conn = _get_db_conn()
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT exhausted_at, cooldown_hours
                        FROM gemini_key_cooldown WHERE key_hash = %s
                    """, (_hash_key(api_key),))
                    row = cur.fetchone()
                    if row is None:
                        return 0.0
                    exhausted_at, cooldown_hours = row
                    now = datetime.now(timezone.utc)
                    if exhausted_at.tzinfo is None:
                        exhausted_at = exhausted_at.replace(tzinfo=timezone.utc)
                    elapsed = (now - exhausted_at).total_seconds() / 3600
                    remaining = cooldown_hours - elapsed
                    return max(0.0, remaining)
            conn.close()
        except Exception:
            return 0.0

    # -----------------------------------------------------------------------
    # Core: get next available key
    # -----------------------------------------------------------------------

    def get_next_key(self) -> tuple[str, str]:
        """
        Available key return করো (round-robin)।

        সব key একবার করে check করে — exhausted না হলে সেটা return করে
        এবং index advance করে পরের call এ পরের key থেকে শুরু হয়।

        Returns:
            (api_key, label) tuple

        Raises:
            RuntimeError: সব key exhausted হলে কত ঘন্টা wait করতে হবে সহ।
        """
        if not self._keys:
            raise RuntimeError(
                "[KeyManager] কোনো Gemini API key পাওয়া যায়নি। "
                ".env ফাইলে GEMINI_API_KEY_1 etc. সেট করো।"
            )

        with self._lock:
            total = len(self._keys)
            # শুরুর index মনে রাখো — full circle ঘুরলে stop
            start = self._index
            for i in range(total):
                idx = (start + i) % total
                key, label = self._keys[idx]
                if not self._is_exhausted(key):
                    # পরের call এ পরের key থেকে শুরু হবে
                    self._index = (idx + 1) % total
                    logger.debug(f"[KeyManager] Using {label} (slot {idx})")
                    return key, label
                else:
                    hrs = self.get_hours_remaining(key)
                    logger.debug(f"[KeyManager] {label} is in cooldown ({hrs:.1f}h left), skipping.")

        # সব key exhausted — কত ঘন্টা বাকি সেটা বলো
        min_wait = min(self.get_hours_remaining(key) for key, _ in self._keys)
        raise RuntimeError(
            f"[KeyManager] সব Gemini API key exhausted! "
            f"আনুমানিক {min_wait:.1f} ঘন্টা পর আবার available হবে।"
        )

    def status(self) -> list[dict]:
        """সব key এর বর্তমান status দেখাও (logging/admin এর জন্য)।"""
        result = []
        for key, label in self._keys:
            exhausted = self._is_exhausted(key)
            hours_left = self.get_hours_remaining(key) if exhausted else 0.0
            result.append({
                "label": label,
                "status": "cooldown" if exhausted else "available",
                "hours_remaining": round(hours_left, 1),
            })
        return result


# ===========================================================================
# Singleton
# ===========================================================================

_key_manager_instance: Optional[GeminiKeyManager] = None
_singleton_lock = threading.Lock()


def get_key_manager() -> GeminiKeyManager:
    """Process-wide singleton GeminiKeyManager return করো।"""
    global _key_manager_instance
    if _key_manager_instance is None:
        with _singleton_lock:
            if _key_manager_instance is None:
                _key_manager_instance = GeminiKeyManager()
    return _key_manager_instance
