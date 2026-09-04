from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path

from halberd import __version__

GITHUB_REPO = "jhueby/halberd"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CACHE_DIR = Path(os.environ.get("HALBERD_DATA_DIR", os.path.expanduser("~/.halberd")))
CACHE_FILE = CACHE_DIR / ".update-check"
CHECK_INTERVAL = 86400  # 24 hours


@dataclass
class UpdateInfo:
    current: str
    latest: str
    url: str
    is_newer: bool


def _parse_version(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.lstrip("v").split(".") if x.isdigit())


def _fetch_latest() -> dict | None:
    req = urllib.request.Request(
        RELEASES_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "halberd-bas"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None


def _read_cache() -> dict | None:
    try:
        if CACHE_FILE.exists():
            data = json.loads(CACHE_FILE.read_text())
            if time.time() - data.get("checked_at", 0) < CHECK_INTERVAL:
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _write_cache(latest_version: str, html_url: str) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps({
            "latest_version": latest_version,
            "html_url": html_url,
            "checked_at": time.time(),
        }))
    except OSError:
        pass


def check_for_update(force: bool = False) -> UpdateInfo | None:
    current = __version__

    if not force:
        cached = _read_cache()
        if cached:
            latest = cached["latest_version"]
            url = cached["html_url"]
            is_newer = _parse_version(latest) > _parse_version(current)
            if is_newer:
                return UpdateInfo(current=current, latest=latest, url=url, is_newer=True)
            return None

    release = _fetch_latest()
    if not release:
        return None

    latest = release.get("tag_name", "").lstrip("v")
    html_url = release.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")

    _write_cache(latest, html_url)

    if not latest:
        return None

    is_newer = _parse_version(latest) > _parse_version(current)
    return UpdateInfo(current=current, latest=latest, url=html_url, is_newer=is_newer)


def startup_update_check() -> str | None:
    """Non-blocking update check for CLI startup. Returns a message or None."""
    try:
        info = check_for_update(force=False)
        if info and info.is_newer:
            return (
                f"Update available: v{info.current} -> v{info.latest}\n"
                f"  {info.url}\n"
                f"  pip install --upgrade halberd-bas"
            )
    except Exception:
        pass
    return None
