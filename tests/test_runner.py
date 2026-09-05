import pytest

from halberd.agent.runner import run_technique, run_chain, TestResult, _build_command, _shell_executable, _test_platforms
from halberd.agent.sandbox import Sandbox, SafetyError
from halberd.library.atomic_schema import AtomicTechnique, AtomicTest, Platform, RiskLevel
from halberd.library.loader import load_chain


class TestRunner:
    def test_dry_run_technique(self):
        sandbox = Sandbox(dry_run=True)
        results = run_technique("T1082", sandbox)
        assert len(results) >= 1
        assert all(r.status in ("dry-run", "skipped") for r in results)
        assert any(r.status == "dry-run" and "Would execute" in r.output for r in results)

    def test_dry_run_chain(self):
        sandbox = Sandbox(dry_run=True)
        chain = load_chain("chain-dns-exfil")
        results = run_chain(chain, sandbox)
        assert len(results) >= 3
        assert all(r.status == "dry-run" for r in results)

    def test_risk_limit_blocks_high_risk(self):
        sandbox = Sandbox(max_risk=RiskLevel.SAFE, dry_run=True)
        results = run_technique("T1048.001", sandbox)
        assert all(r.status == "skipped" for r in results)

    def test_safe_technique_passes_risk_check(self):
        sandbox = Sandbox(max_risk=RiskLevel.SAFE, dry_run=True)
        results = run_technique("T1082", sandbox)
        assert any(r.status == "dry-run" for r in results)

    def test_missing_technique(self):
        sandbox = Sandbox(dry_run=True)
        results = run_technique("T9999.999", sandbox)
        assert len(results) == 0 or results[0].status == "error"


class TestPlatformExecution:
    def test_build_command_bash(self):
        result = _build_command("echo hello", "bash")
        assert result == "echo hello"

    def test_build_command_powershell(self):
        result = _build_command("Get-Date", "powershell")
        assert result == ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-Date"]

    def test_build_command_cmd(self):
        result = _build_command("dir", "cmd")
        assert result == ["cmd", "/C", "dir"]

    def test_build_command_python(self):
        result = _build_command("print(1)", "python")
        assert result == ["python3", "-c", "print(1)"]

    def test_shell_executable_bash(self):
        assert _shell_executable("bash") == "/bin/bash"

    def test_shell_executable_powershell(self):
        assert _shell_executable("powershell") is None

    def test_test_platforms_inherits(self):
        tech = AtomicTechnique(
            id="T0001", name="T", tactic="discovery", technique="T",
            platforms=[Platform.LINUX, Platform.WINDOWS], description="T",
            tests=[AtomicTest(name="t", command="echo")],
        )
        assert _test_platforms(tech, tech.tests[0]) == ["linux", "windows"]

    def test_test_platforms_overrides(self):
        tech = AtomicTechnique(
            id="T0001", name="T", tactic="discovery", technique="T",
            platforms=[Platform.LINUX, Platform.WINDOWS], description="T",
            tests=[AtomicTest(name="t", command="echo", platforms=[Platform.LINUX])],
        )
        assert _test_platforms(tech, tech.tests[0]) == ["linux"]

    def test_dry_run_shows_executor(self):
        sandbox = Sandbox(dry_run=True)
        results = run_technique("T1082", sandbox)
        assert len(results) >= 1
        has_bash = any("bash" in r.output for r in results if r.status == "dry-run")
        assert has_bash

    def test_dry_run_skips_wrong_platform_tests(self):
        sandbox = Sandbox(dry_run=True)
        results = run_technique("T1082", sandbox)
        for r in results:
            assert r.status in ("dry-run", "skipped")

    def test_windows_only_technique_skipped_on_linux(self):
        sandbox = Sandbox(dry_run=True)
        results = run_technique("T1059.001", sandbox)
        assert all(r.status == "skipped" for r in results)

    def test_cross_platform_technique_has_multiple_tests(self):
        from halberd.library.loader import load_atomic
        tech = load_atomic("T1082")
        assert len(tech.tests) >= 3
        platforms_covered = set()
        for test in tech.tests:
            if test.platforms:
                for p in test.platforms:
                    platforms_covered.add(p.value)
        assert "linux" in platforms_covered
        assert "windows" in platforms_covered
        assert "macos" in platforms_covered


class TestCleanup:
    def test_clean_technique_check_only(self):
        from halberd.agent.cleanup import clean_technique

        report = clean_technique("T1053.003", check_only=True)
        assert len(report.actions) >= 1
        has_cleanup = any(a.status == "skipped" and a.command for a in report.actions)
        assert has_cleanup

    def test_clean_technique_missing(self):
        from halberd.agent.cleanup import clean_technique

        report = clean_technique("T9999.999")
        assert len(report.actions) == 1
        assert report.actions[0].status == "failed"

    def test_clean_all_check_only(self):
        from halberd.agent.cleanup import clean_all

        report = clean_all(check_only=True)
        assert len(report.actions) >= 10

    def test_clean_technique_no_cleanup(self):
        from halberd.agent.cleanup import clean_technique

        report = clean_technique("T1082", check_only=True)
        assert all(a.status in ("skipped", "no-cleanup") for a in report.actions)

    def test_clean_technique_runs_cleanup(self):
        from halberd.agent.cleanup import clean_technique

        report = clean_technique("T1053.003")
        assert any(a.status in ("cleaned", "failed") for a in report.actions)

    def test_cleanup_report_summary(self):
        from halberd.agent.cleanup import CleanupReport, CleanupAction

        report = CleanupReport(actions=[
            CleanupAction(technique_id="T1", test_name="t", status="cleaned"),
            CleanupAction(technique_id="T2", test_name="t", status="no-cleanup"),
        ])
        assert "1 cleaned" in report.summary()
        assert "1 have no cleanup command" in report.summary()

    def test_cleanup_filters_by_platform(self):
        from halberd.agent.cleanup import clean_technique

        report = clean_technique("T1082", check_only=True)
        for action in report.actions:
            assert "Windows" not in action.test_name or action.test_name == ""

    def test_cleanup_skips_windows_only_technique(self):
        from halberd.agent.cleanup import clean_technique

        report = clean_technique("T1059.001", check_only=True)
        assert len(report.actions) == 0

    def test_cleanup_all_respects_platform(self):
        from halberd.agent.cleanup import clean_all

        report = clean_all(check_only=True)
        for action in report.actions:
            assert "PowerShell" not in action.test_name


class TestSandbox:
    def test_risk_check(self):
        from halberd.library.loader import load_atomic

        sandbox = Sandbox(max_risk=RiskLevel.LOW)
        medium_tech = load_atomic("T1048.001")
        with pytest.raises(SafetyError):
            sandbox.check_technique(medium_tech)

    def test_risk_allows_within_limit(self):
        from halberd.library.loader import load_atomic

        sandbox = Sandbox(max_risk=RiskLevel.MEDIUM)
        tech = load_atomic("T1082")
        sandbox.check_technique(tech)
