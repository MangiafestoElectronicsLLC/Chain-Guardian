import os
import json
from cryptography.fernet import Fernet
from .config import APP_DIRNAME, KEY_FILENAME, STORE_FILENAME

def _app_dir():
    return os.path.join(os.path.expanduser("~"), APP_DIRNAME)

def _key_path():
    return os.path.join(_app_dir(), KEY_FILENAME)

def _store_path():
    return os.path.join(_app_dir(), STORE_FILENAME)

def _ensure_app_dir():
    d = _app_dir()
    os.makedirs(d, exist_ok=True)
    return d

def _load_or_create_key():
    _ensure_app_dir()
    kp = _key_path()
    if os.path.exists(kp):
        with open(kp, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(kp, "wb") as f:
        f.write(key)
    return key

def load_store():
    _ensure_app_dir()
    key = _load_or_create_key()
    f = Fernet(key)
    sp = _store_path()
    if not os.path.exists(sp):
        return {"settings": {}, "api_keys": {}, "orders": [], "tracked_addresses": {"btc": [], "eth": []}}
    with open(sp, "rb") as fh:
        enc = fh.read()
    try:
        raw = f.decrypt(enc)
        data = json.loads(raw.decode("utf-8"))
        return data
    except Exception:
        # If corruption or key mismatch, do not crash; start fresh.
        return {"settings": {}, "api_keys": {}, "orders": [], "tracked_addresses": {"btc": [], "eth": []}}

def save_store(store: dict):
    _ensure_app_dir()
    key = _load_or_create_key()
    f = Fernet(key)
    raw = json.dumps(store, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    enc = f.encrypt(raw)
    with open(_store_path(), "wb") as fh:
        fh.write(enc)
