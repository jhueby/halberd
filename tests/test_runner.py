import pytest

from halberd.agent.runner import run_technique, run_chain, TestResult
from halberd.agent.sandbox import Sandbox, SafetyError
from halberd.library.atomic_schema import RiskLevel
from halberd.library.loader import load_chain


class TestRunner:
    def test_dry_run_technique(self):
        sandbox = Sandbox(dry_run=True)
        results = run_technique("T1082", sandbox)
        assert len(results) >= 1
        assert all(r.status == "dry-run" for r in results)
        assert "Would execute" in results[0].output

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
        assert len(report.actions) >= 15

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
