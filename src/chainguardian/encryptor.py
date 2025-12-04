import json
from cryptography.fernet import Fernet
from .config import FERNET_KEYFILE, STORE_FILE, DEFAULTS
from pathlib import Path

def ensure_key():
    if not FERNET_KEYFILE.exists():
        key = Fernet.generate_key()
        FERNET_KEYFILE.write_bytes(key)
    return FERNET_KEYFILE.read_bytes()

FERNET_KEY = ensure_key()
FERNET = Fernet(FERNET_KEY)

def save_store(payload: dict):
    # ensure settings defaults
    payload.setdefault("settings", {})
    for k, v in DEFAULTS.items():
        payload["settings"].setdefault(k, v)
    data = json.dumps(payload).encode("utf-8")
    token = FERNET.encrypt(data)
    STORE_FILE.write_bytes(token)

def load_store():
    if not STORE_FILE.exists():
        # return skeleton
        return {"api_keys": {}, "orders": [], "tracked_addresses": {"btc": [], "eth": []}, "settings": DEFAULTS.copy()}
    token = STORE_FILE.read_bytes()
    try:
        data = FERNET.decrypt(token)
        return json.loads(data.decode("utf-8"))
    except Exception:
        # fallback to empty safe store
        return {"api_keys": {}, "orders": [], "tracked_addresses": {"btc": [], "eth": []}, "settings": DEFAULTS.copy()}
