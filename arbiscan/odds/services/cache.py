import json
import os
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent.parent / ".api_cache"
CACHE_DIR.mkdir(exist_ok=True)


def cache_key(endpoint: str, params: dict) -> str:
    import hashlib
    raw = endpoint + json.dumps(params, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def get_cached(endpoint: str, params: dict, ttl_seconds: int = 3600):
    key  = cache_key(endpoint, params)
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        age = time.time() - path.stat().st_mtime
        if age < ttl_seconds:
            with open(path) as f:
                data = json.load(f)
            print(f"  [CACHE HIT] {endpoint} (age: {int(age)}s)")
            return data
    return None


def set_cached(endpoint: str, params: dict, data):
    key  = cache_key(endpoint, params)
    path = CACHE_DIR / f"{key}.json"
    with open(path, "w") as f:
        json.dump(data, f)


def clear_cache():
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
    print(f"Cache cleared: {CACHE_DIR}")
