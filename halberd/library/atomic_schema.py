from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Platform(str, Enum):
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"


class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


RISK_ORDER = {RiskLevel.SAFE: 0, RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3}


class ExpectedArtifact(BaseModel):
    type: str = Field(description="Artifact category: process, file_modification, network, registry")
    value: str = Field(description="Pattern or path the EDR should observe")


class AtomicTest(BaseModel):
    name: str
    executor: str = Field(default="bash", description="Shell or executor: bash, powershell, cmd, python")
    platforms: list[Platform] | None = Field(default=None, description="Platforms this test runs on; inherits from technique if omitted")
    command: str = Field(description="Command(s) to execute")
    cleanup: str | None = Field(default=None, description="Reversal command(s)")
    expected_artifacts: list[ExpectedArtifact] = Field(default_factory=list)
    detection_notes: str | None = None
    elevation_required: bool = False


class AtomicTechnique(BaseModel):
    id: str = Field(description="MITRE ATT&CK technique ID, e.g. T1059.004")
    name: str
    tactic: str = Field(description="ATT&CK tactic: initial-access, execution, persistence, etc.")
    technique: str = Field(description="Full ATT&CK technique name")
    platforms: list[Platform]
    risk: RiskLevel = RiskLevel.LOW
    description: str
    tests: list[AtomicTest] = Field(min_length=1)

    @property
    def risk_value(self) -> int:
        return RISK_ORDER[self.risk]

    def tests_for_platform(self, platform: str) -> list[AtomicTest]:
        result = []
        for test in self.tests:
            effective = [p.value for p in test.platforms] if test.platforms else [p.value for p in self.platforms]
            if platform in effective:
                result.append(test)
        return result
