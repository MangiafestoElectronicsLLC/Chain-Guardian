import os
import json
from cryptography.fernet import Fernet
from pathlib import Path
from .config import APP_DIRNAME, STORE_FILENAME, KEY_FILENAME

def _app_dir() -> Path:
    p = Path.home() / APP_DIRNAME
    p.mkdir(parents=True, exist_ok=True)
    return p

def _key_path() -> Path:
    return _app_dir() / KEY_FILENAME

def _store_path() -> Path:
    return _app_dir() / STORE_FILENAME

def _get_fernet() -> Fernet:
    kp = _key_path()
    if not kp.exists():
        kp.write_bytes(Fernet.generate_key())
    key = kp.read_bytes()
    return Fernet(key)

def load_store() -> dict:
    sp = _store_path()
    f = _get_fernet()
    if not sp.exists():
        # initialize default store
        store = {
            "api_keys": {},
            "settings": {"refresh_seconds": 30, "default_quote": "USDT", "profit_pct_to_take": 300.0},
            "orders": [],  # list of dicts {id, asset, side, amount, price, exchange, timestamp, note, status}
            "tracked_addresses": {"btc": [], "eth": []},
            "whale_watch": {"btc": [], "eth": []}
        }
        save_store(store)
        return store
    try:
        data = f.decrypt(sp.read_bytes())
        return json.loads(data.decode("utf-8"))
    except Exception:
        # if decrypt fails, don't crash—create a new store (and keep the old file)
        return {
            "api_keys": {},
            "settings": {"refresh_seconds": 30, "default_quote": "USDT", "profit_pct_to_take": 300.0},
            "orders": [],
            "tracked_addresses": {"btc": [], "eth": []},
            "whale_watch": {"btc": [], "eth": []}
        }

def save_store(store: dict) -> None:
    sp = _store_path()
    f = _get_fernet()
    blob = json.dumps(store, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sp.write_bytes(f.encrypt(blob))
