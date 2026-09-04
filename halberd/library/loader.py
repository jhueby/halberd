from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .atomic_schema import AtomicTechnique
from .chain_schema import AttackChain

_LIBRARY_DIR = Path(__file__).parent
ATOMIC_DIR = _LIBRARY_DIR / "atomic"
CHAINS_DIR = _LIBRARY_DIR / "chains"


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_atomic(technique_id: str) -> AtomicTechnique:
    candidates = list(ATOMIC_DIR.glob(f"{technique_id}.yml")) + list(ATOMIC_DIR.glob(f"{technique_id}.yaml"))
    if not candidates:
        raise FileNotFoundError(f"No atomic test found for {technique_id}")
    return AtomicTechnique(**_load_yaml(candidates[0]))


def load_all_atomics() -> list[AtomicTechnique]:
    techniques = []
    for path in sorted(ATOMIC_DIR.glob("*.yml")):
        try:
            techniques.append(AtomicTechnique(**_load_yaml(path)))
        except (ValidationError, Exception) as e:
            print(f"Warning: skipping {path.name}: {e}")
    return techniques


def load_chain(chain_id: str) -> AttackChain:
    candidates = list(CHAINS_DIR.glob(f"{chain_id}.yml")) + list(CHAINS_DIR.glob(f"{chain_id}.yaml"))
    if candidates:
        return AttackChain(**_load_yaml(candidates[0]))
    for path in CHAINS_DIR.glob("*.yml"):
        data = _load_yaml(path)
        if data.get("id") == chain_id:
            return AttackChain(**data)
    raise FileNotFoundError(f"No attack chain found for {chain_id}")


def load_all_chains() -> list[AttackChain]:
    chains = []
    for path in sorted(CHAINS_DIR.glob("*.yml")):
        try:
            chains.append(AttackChain(**_load_yaml(path)))
        except (ValidationError, Exception) as e:
            print(f"Warning: skipping {path.name}: {e}")
    return chains


def validate_chain_references(chain: AttackChain) -> list[str]:
    """Return list of technique IDs referenced by chain that don't exist in the atomic library."""
    available = {t.id for t in load_all_atomics()}
    return [step.technique for step in chain.steps if step.technique not in available]


def get_technique_index() -> dict[str, AtomicTechnique]:
    return {t.id: t for t in load_all_atomics()}
