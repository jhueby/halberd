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


@dataclass
class LibraryUpdateResult:
    new_atomics: list[str]
    updated_atomics: list[str]
    new_chains: list[str]
    updated_chains: list[str]

    @property
    def total_changes(self) -> int:
        return len(self.new_atomics) + len(self.updated_atomics) + len(self.new_chains) + len(self.updated_chains)

    def summary(self) -> str:
        parts = []
        if self.new_atomics:
            parts.append(f"{len(self.new_atomics)} new techniques")
        if self.updated_atomics:
            parts.append(f"{len(self.updated_atomics)} updated techniques")
        if self.new_chains:
            parts.append(f"{len(self.new_chains)} new chains")
        if self.updated_chains:
            parts.append(f"{len(self.updated_chains)} updated chains")
        return ", ".join(parts) if parts else "Library is up to date"


def _github_api(path: str) -> dict | list | None:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/{path}"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "halberd-bas"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None


def _download_raw(path: str) -> str | None:
    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "halberd-bas"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError):
        return None


def _sync_directory(github_path: str, local_dir: Path, extension: str = ".yml") -> tuple[list[str], list[str]]:
    """Sync a GitHub directory to a local directory. Returns (new_files, updated_files)."""
    contents = _github_api(f"contents/{github_path}")
    if not contents or not isinstance(contents, list):
        return [], []

    new_files = []
    updated_files = []

    remote_files = [f for f in contents if f.get("name", "").endswith(extension)]

    for file_info in remote_files:
        name = file_info["name"]
        remote_sha = file_info.get("sha", "")
        download_path = file_info.get("path", f"{github_path}/{name}")
        local_path = local_dir / name

        if local_path.exists():
            local_content = local_path.read_text()
            remote_content = _download_raw(download_path)
            if remote_content is None:
                continue
            if local_content.strip() != remote_content.strip():
                local_path.write_text(remote_content)
                updated_files.append(name)
        else:
            remote_content = _download_raw(download_path)
            if remote_content is None:
                continue
            local_path.write_text(remote_content)
            new_files.append(name)

    return new_files, updated_files


def update_library() -> LibraryUpdateResult:
    """Pull the latest techniques and chains from the GitHub repo."""
    from halberd.library.loader import ATOMIC_DIR, CHAINS_DIR

    new_at, upd_at = _sync_directory("halberd/library/atomic", ATOMIC_DIR)
    new_ch, upd_ch = _sync_directory("halberd/library/chains", CHAINS_DIR)

    return LibraryUpdateResult(
        new_atomics=new_at,
        updated_atomics=upd_at,
        new_chains=new_ch,
        updated_chains=upd_ch,
    )


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
