from __future__ import annotations

import os

from halberd.library.atomic_schema import AtomicTechnique, AtomicTest, RiskLevel, RISK_ORDER


class SafetyError(Exception):
    pass


class Sandbox:
    def __init__(
        self,
        max_risk: RiskLevel = RiskLevel.MEDIUM,
        allow_root: bool = False,
        dry_run: bool = False,
    ):
        self.max_risk = max_risk
        self.allow_root = allow_root
        self.dry_run = dry_run

    def check_technique(self, technique: AtomicTechnique) -> None:
        if RISK_ORDER[technique.risk] > RISK_ORDER[self.max_risk]:
            raise SafetyError(
                f"Technique {technique.id} risk level '{technique.risk.value}' "
                f"exceeds max allowed '{self.max_risk.value}'"
            )

    def check_test(self, test: AtomicTest) -> None:
        if test.elevation_required and not self._is_root():
            raise SafetyError(
                f"Test '{test.name}' requires elevation but agent is not running as root"
            )
        if self._is_root() and not self.allow_root:
            raise SafetyError(
                "Agent is running as root but --allow-root was not passed. "
                "Running attack simulations as root can cause system damage."
            )

    def _is_root(self) -> bool:
        return hasattr(os, "geteuid") and os.geteuid() == 0
