from __future__ import annotations

import glob
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from halberd.library.atomic_schema import AtomicTechnique
from halberd.library.loader import load_all_atomics, load_atomic


@dataclass
class CleanupAction:
    technique_id: str
    test_name: str
    status: str  # cleaned, skipped, failed, no-cleanup
    command: str = ""
    output: str = ""
    error: str = ""
    duration: float = 0.0


@dataclass
class ArtifactHit:
    technique_id: str
    test_name: str
    artifact_type: str
    pattern: str
    found: list[str] = field(default_factory=list)


@dataclass
class CleanupReport:
    actions: list[CleanupAction] = field(default_factory=list)
    artifacts: list[ArtifactHit] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def cleaned_count(self) -> int:
        return sum(1 for a in self.actions if a.status == "cleaned")

    @property
    def failed_count(self) -> int:
        return sum(1 for a in self.actions if a.status == "failed")

    @property
    def artifact_count(self) -> int:
        return sum(len(a.found) for a in self.artifacts)

    def summary(self) -> str:
        parts = []
        if self.cleaned_count:
            parts.append(f"{self.cleaned_count} cleaned")
        if self.failed_count:
            parts.append(f"{self.failed_count} failed")
        no_cleanup = sum(1 for a in self.actions if a.status == "no-cleanup")
        if no_cleanup:
            parts.append(f"{no_cleanup} have no cleanup command")
        if self.artifact_count:
            parts.append(f"{self.artifact_count} residual artifacts detected")
        return ", ".join(parts) if parts else "Nothing to clean"


def _run_cleanup_command(command: str, timeout: int = 30) -> tuple[str, str, float, bool]:
    start = time.monotonic()
    try:
        result = subprocess.run(
            command,
            shell=True,
            executable="/bin/bash",
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.monotonic() - start
        return result.stdout[:1024], result.stderr[:1024], duration, result.returncode == 0
    except subprocess.TimeoutExpired:
        return "", f"Timed out after {timeout}s", float(timeout), False
    except Exception as e:
        return "", str(e), time.monotonic() - start, False


def _check_file_artifacts(pattern: str) -> list[str]:
    if not pattern.startswith("/"):
        return []
    return glob.glob(pattern)


def clean_technique(
    technique_id: str,
    check_only: bool = False,
    timeout: int = 30,
) -> CleanupReport:
    report = CleanupReport()

    try:
        technique = load_atomic(technique_id)
    except FileNotFoundError:
        report.actions.append(CleanupAction(
            technique_id=technique_id,
            test_name="N/A",
            status="failed",
            error=f"Technique {technique_id} not found in library",
        ))
        return report

    for test in technique.tests:
        if not test.cleanup:
            report.actions.append(CleanupAction(
                technique_id=technique.id,
                test_name=test.name,
                status="no-cleanup",
            ))
        elif check_only:
            report.actions.append(CleanupAction(
                technique_id=technique.id,
                test_name=test.name,
                status="skipped",
                command=test.cleanup.strip(),
            ))
        else:
            stdout, stderr, duration, ok = _run_cleanup_command(test.cleanup, timeout)
            report.actions.append(CleanupAction(
                technique_id=technique.id,
                test_name=test.name,
                status="cleaned" if ok else "failed",
                command=test.cleanup.strip(),
                output=stdout,
                error=stderr,
                duration=duration,
            ))

        for artifact in test.expected_artifacts:
            if artifact.type == "file_modification":
                hits = _check_file_artifacts(artifact.value)
                if hits:
                    report.artifacts.append(ArtifactHit(
                        technique_id=technique.id,
                        test_name=test.name,
                        artifact_type=artifact.type,
                        pattern=artifact.value,
                        found=hits,
                    ))

    return report


def clean_all(
    check_only: bool = False,
    timeout: int = 30,
) -> CleanupReport:
    combined = CleanupReport()

    for technique in load_all_atomics():
        report = clean_technique(technique.id, check_only=check_only, timeout=timeout)
        combined.actions.extend(report.actions)
        combined.artifacts.extend(report.artifacts)

    return combined
