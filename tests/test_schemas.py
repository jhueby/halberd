import pytest
from pydantic import ValidationError

from halberd.library.atomic_schema import AtomicTechnique, AtomicTest, RiskLevel, Platform
from halberd.library.chain_schema import AttackChain, ChainStep


class TestAtomicSchema:
    def test_valid_technique(self):
        t = AtomicTechnique(
            id="T1082",
            name="System Info Discovery",
            tactic="discovery",
            technique="System Information Discovery",
            platforms=[Platform.LINUX],
            risk=RiskLevel.SAFE,
            description="Test",
            tests=[AtomicTest(name="test", command="echo hi")],
        )
        assert t.id == "T1082"
        assert t.risk_value == 0

    def test_technique_requires_tests(self):
        with pytest.raises(ValidationError):
            AtomicTechnique(
                id="T9999",
                name="No Tests",
                tactic="discovery",
                technique="Test",
                platforms=[Platform.LINUX],
                description="Test",
                tests=[],
            )

    def test_risk_ordering(self):
        t_safe = AtomicTechnique(
            id="T0001", name="Safe", tactic="discovery", technique="T",
            platforms=[Platform.LINUX], risk=RiskLevel.SAFE, description="T",
            tests=[AtomicTest(name="t", command="echo")],
        )
        t_high = AtomicTechnique(
            id="T0002", name="High", tactic="discovery", technique="T",
            platforms=[Platform.LINUX], risk=RiskLevel.HIGH, description="T",
            tests=[AtomicTest(name="t", command="echo")],
        )
        assert t_safe.risk_value < t_high.risk_value


class TestChainSchema:
    def test_valid_chain(self):
        c = AttackChain(
            id="chain-test",
            name="Test Chain",
            description="A test",
            mitre_tactics=["discovery"],
            steps=[ChainStep(technique="T1082")],
        )
        assert len(c.steps) == 1
        assert c.steps[0].delay_after == 5

    def test_chain_requires_steps(self):
        with pytest.raises(ValidationError):
            AttackChain(
                id="chain-empty",
                name="Empty",
                description="No steps",
                mitre_tactics=["discovery"],
                steps=[],
            )

    def test_chain_import_source(self):
        c = AttackChain(
            id="chain-imported",
            name="Imported",
            description="From URL",
            mitre_tactics=["discovery"],
            steps=[ChainStep(technique="T1082")],
            import_source="https://example.com/chain.yml",
        )
        assert c.import_source == "https://example.com/chain.yml"
