from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from halberd.agent.platform_info import current_platform
from halberd.agent.sandbox import Sandbox, SafetyError
from halberd.library.atomic_schema import AtomicTechnique, AtomicTest
from halberd.library.chain_schema import AttackChain
from halberd.library.loader import load_atomic, load_all_atomics


@dataclass
class TestResult:
    technique_id: str
    test_name: str
    status: str  # success, failed, skipped, error, dry-run
    output: str = ""
    error: str = ""
    duration: float = 0.0
    cleanup_output: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _shell_executable(executor: str) -> str | None:
    if executor == "bash":
        return "/bin/bash"
    if executor == "zsh":
        return "/bin/zsh"
    if executor in ("powershell", "cmd", "python"):
        return None
    return None


def _build_command(command: str, executor: str) -> str | list[str]:
    if executor == "powershell":
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
    if executor == "cmd":
        return ["cmd", "/C", command]
    if executor == "python":
        return ["python3", "-c", command]
    return command


def _test_platforms(technique: AtomicTechnique, test: AtomicTest) -> list[str]:
    if test.platforms:
        return [p.value for p in test.platforms]
    return [p.value for p in technique.platforms]


def run_test(
    technique: AtomicTechnique,
    test: AtomicTest,
    sandbox: Sandbox,
    timeout: int = 60,
) -> TestResult:
    try:
        sandbox.check_technique(technique)
        sandbox.check_test(test)
    except SafetyError as e:
        return TestResult(
            technique_id=technique.id,
            test_name=test.name,
            status="skipped",
            error=str(e),
        )

    plat = current_platform()
    test_plats = _test_platforms(technique, test)
    if plat not in test_plats:
        return TestResult(
            technique_id=technique.id,
            test_name=test.name,
            status="skipped",
            error=f"Platform '{plat}' not supported (requires {test_plats})",
        )

    if sandbox.dry_run:
        return TestResult(
            technique_id=technique.id,
            test_name=test.name,
            status="dry-run",
            output=f"Would execute ({test.executor}):\n{test.command}",
        )

    cmd = _build_command(test.command, test.executor)
    use_shell = test.executor in ("bash", "zsh")
    executable = _shell_executable(test.executor)

    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            shell=use_shell,
            executable=executable,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.monotonic() - start

        test_result = TestResult(
            technique_id=technique.id,
            test_name=test.name,
            status="success" if result.returncode == 0 else "failed",
            output=result.stdout[:4096],
            error=result.stderr[:2048],
            duration=duration,
        )
    except subprocess.TimeoutExpired:
        test_result = TestResult(
            technique_id=technique.id,
            test_name=test.name,
            status="error",
            error=f"Timed out after {timeout}s",
            duration=timeout,
        )
    except Exception as e:
        test_result = TestResult(
            technique_id=technique.id,
            test_name=test.name,
            status="error",
            error=str(e),
            duration=time.monotonic() - start,
        )

    if test.cleanup and not sandbox.dry_run:
        try:
            cleanup_cmd = _build_command(test.cleanup, test.executor)
            cleanup = subprocess.run(
                cleanup_cmd,
                shell=use_shell,
                executable=executable,
                capture_output=True,
                text=True,
                timeout=30,
            )
            test_result.cleanup_output = cleanup.stdout[:1024]
        except Exception:
            test_result.cleanup_output = "cleanup failed"

    return test_result


def run_technique(
    technique_id: str,
    sandbox: Sandbox,
    test_index: int | None = None,
    timeout: int = 60,
) -> list[TestResult]:
    try:
        technique = load_atomic(technique_id)
    except FileNotFoundError:
        return [TestResult(
            technique_id=technique_id,
            test_name="N/A",
            status="error",
            error=f"Technique {technique_id} not found in library",
        )]
    results = []

    if test_index is not None:
        if test_index >= len(technique.tests):
            return [TestResult(
                technique_id=technique_id,
                test_name="N/A",
                status="error",
                error=f"Test index {test_index} out of range (max {len(technique.tests) - 1})",
            )]
        tests_to_run = [technique.tests[test_index]]
    else:
        tests_to_run = technique.tests

    for test in tests_to_run:
        results.append(run_test(technique, test, sandbox, timeout))

    return results


def run_chain(
    chain: AttackChain,
    sandbox: Sandbox,
    timeout: int = 60,
) -> list[TestResult]:
    results = []

    for step in chain.steps:
        step_results = run_technique(
            step.technique,
            sandbox,
            test_index=step.test_index,
            timeout=timeout,
        )
        results.extend(step_results)

        aborted = any(r.status == "error" and step.on_failure == "abort" for r in step_results)
        if aborted:
            break

        if step.delay_after > 0 and not sandbox.dry_run:
            time.sleep(step.delay_after)

    return results
