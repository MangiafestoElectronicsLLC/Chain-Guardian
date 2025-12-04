# lightweight wrapper if you want to extend to sqlite later.
import json
from typing import Dict, Any

def export_plain(store: Dict[str, Any], path: str):
    with open(path, "w") as f:
        json.dump(store, f, indent=2)
