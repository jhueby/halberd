from __future__ import annotations

from pydantic import BaseModel, Field


class ChainStep(BaseModel):
    technique: str = Field(description="ATT&CK technique ID referencing an atomic test")
    test_index: int = Field(default=0, description="Which test within the technique to run")
    delay_after: int = Field(default=5, description="Seconds to wait after this step")
    inputs: dict[str, str] = Field(
        default_factory=dict,
        description="Override variables passed to the test command",
    )
    on_failure: str = Field(default="continue", description="continue | abort")


class AttackChain(BaseModel):
    id: str = Field(description="Unique chain identifier, e.g. chain-dns-exfil")
    name: str
    description: str
    mitre_tactics: list[str] = Field(description="Tactics covered by this chain")
    steps: list[ChainStep] = Field(min_length=1)
    import_source: str | None = Field(
        default=None,
        description="URL or file path this chain was imported from",
    )
    tags: list[str] = Field(default_factory=list)
