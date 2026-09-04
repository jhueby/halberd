from __future__ import annotations

import abc
import shutil
from pathlib import Path

import yaml

from .chain_schema import AttackChain
from .loader import CHAINS_DIR, validate_chain_references


class ImportBackend(abc.ABC):
    @abc.abstractmethod
    def fetch(self, source: str) -> dict:
        ...


class FileImporter(ImportBackend):
    def fetch(self, source: str) -> dict:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        with open(path) as f:
            return yaml.safe_load(f)


class URLImporter(ImportBackend):
    def fetch(self, source: str) -> dict:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx is required for URL imports: pip install httpx")
        resp = httpx.get(source, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        return yaml.safe_load(resp.text)


class DocImporter(ImportBackend):
    """Placeholder for future blog-post / document to attack-chain converter."""

    def fetch(self, source: str) -> dict:
        raise NotImplementedError(
            "Document-to-chain import is planned for v2. "
            "It will accept a blog post URL or uploaded document and use NLP "
            "to extract the attack chain, mapping steps to ATT&CK techniques. "
            "For now, manually create the chain YAML and use file or URL import."
        )


def _detect_backend(source: str) -> ImportBackend:
    if source.startswith(("http://", "https://")):
        return URLImporter()
    path = Path(source)
    if path.exists() or path.suffix in (".yml", ".yaml", ".json"):
        return FileImporter()
    return DocImporter()


def import_chain(
    source: str,
    backend: ImportBackend | None = None,
    save: bool = True,
) -> AttackChain:
    if backend is None:
        backend = _detect_backend(source)

    raw = backend.fetch(source)
    raw.setdefault("import_source", source)

    chain = AttackChain(**raw)

    missing = validate_chain_references(chain)
    if missing:
        print(
            f"Warning: chain '{chain.id}' references techniques not in the "
            f"atomic library: {', '.join(missing)}"
        )

    if save:
        dest = CHAINS_DIR / f"{chain.id}.yml"
        with open(dest, "w") as f:
            yaml.dump(raw, f, default_flow_style=False, sort_keys=False)
        print(f"Saved chain to {dest}")

    return chain


def import_chain_from_file(path: str, save: bool = True) -> AttackChain:
    return import_chain(path, backend=FileImporter(), save=save)


def import_chain_from_url(url: str, save: bool = True) -> AttackChain:
    return import_chain(url, backend=URLImporter(), save=save)
