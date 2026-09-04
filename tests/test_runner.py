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
