"""vault.py: pre-processed public audio vault (metadata in Supabase, files in Storage).

Zero compute: users stream ready-made vocal-only / instrument-free tracks.
Falls back to vault_catalog.json if Supabase is unreachable or the table is empty.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import streamlit as st

log = logging.getLogger(__name__)
LOCAL_CATALOG = Path(__file__).parent / "vault_catalog.json"


def _local_tracks() -> list[dict]:
    try:
        return json.loads(LOCAL_CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        log.exception("Could not read local vault catalog")
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def load_vault(_client, category: Optional[str] = None, trigger: Optional[str] = None,
               stage: Optional[int] = None) -> list[dict]:
    """_client is your cached Supabase client (leading underscore = not hashed)."""
    rows: list[dict] = []
    try:
        q = _client.table("vault_tracks").select("*").eq("is_active", True)
        if category:
            q = q.eq("category", category)
        if trigger:
            q = q.contains("triggers", [trigger])
        if stage:
            q = q.contains("stages", [stage])
        rows = q.order("title").execute().data or []
    except Exception:
        log.exception("Vault query failed, using local catalog")

    if rows:
        return rows

    # fallback: same filters in Python
    out = []
    for t in _local_tracks():
        if not t.get("is_active", True):
            continue
        if category and t.get("category") != category:
            continue
        if trigger and trigger not in t.get("triggers", []):
            continue
        if stage and stage not in t.get("stages", []):
            continue
        out.append(t)
    return out


def seed_vault(client) -> int:
    """Run ONCE locally with a service-role key (anon key can't write): pushes the JSON into Supabase."""
    rows = [t for t in _local_tracks() if "REPLACE_ME" not in t.get("audio_url", "")]
    if rows:
        client.table("vault_tracks").upsert(rows).execute()
    return len(rows)
