from chainguardian.encryptor import save_store, load_store
import tempfile, os, json

def test_encrypt_save_load(tmp_path):
    store = {"api_keys": {"foo": {"k":"v"}}, "orders": [], "tracked_addresses": {"btc": [], "eth": []}, "settings": {}}
    save_store(store)
    loaded = load_store()
    assert "api_keys" in loaded
