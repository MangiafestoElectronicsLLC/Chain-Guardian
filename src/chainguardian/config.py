import os
from pathlib import Path
HOME = Path.home()
APP_DIR = HOME / ".chainguardian"
APP_DIR.mkdir(parents=True, exist_ok=True)
FERNET_KEYFILE = APP_DIR / "fernet.key"
STORE_FILE = APP_DIR / "store.enc"

# default settings
DEFAULTS = {
    "refresh_seconds": 30,
    "fear_buy_threshold": 20,
    "profit_pct_to_take": 300.0,
    "default_quote": "USDT"
}
