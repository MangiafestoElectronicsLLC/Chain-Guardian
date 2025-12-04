import os, json
from cryptography.fernet import Fernet
from pathlib import Path
from .config import APP_DIRNAME, STORE_FILENAME, KEY_FILENAME

def _app_dir():
    p = Path.home() / APP_DIRNAME
    p.mkdir(parents=True, exist_ok=True)
    return p

def _key_path(): return _app_dir() / KEY_FILENAME
def _store_path(): return _app_dir() / STORE_FILENAME

def _get_fernet():
    kp = _key_path()
    if not kp.exists():
        kp.write_bytes(Fernet.generate_key())
    return Fernet(kp.read_bytes())

def load_store():
    sp = _store_path()
    f = _get_fernet()
    if not sp.exists():
        store = {"api_keys": {}, "settings": {"refresh_seconds":30,"default_quote":"USDT","profit_pct_to_take":300.0}, "orders": []}
        save_store(store)
        return store
    try:
        return json.loads(f.decrypt(sp.read_bytes()).decode("utf-8"))
    except Exception:
        return {"api_keys": {}, "settings": {}, "orders": []}

def save_store(store):
    sp = _store_path()
    f = _get_fernet()
    blob = json.dumps(store).encode("utf-8")
    sp.write_bytes(f.encrypt(blob))
