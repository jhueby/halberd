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


class TestPerPlatformTests:
    def test_test_inherits_technique_platforms(self):
        t = AtomicTechnique(
            id="T0001", name="Multi", tactic="discovery", technique="T",
            platforms=[Platform.LINUX, Platform.WINDOWS], description="T",
            tests=[AtomicTest(name="default", command="echo")],
        )
        assert t.tests_for_platform("linux") == [t.tests[0]]
        assert t.tests_for_platform("windows") == [t.tests[0]]

    def test_test_overrides_platforms(self):
        t = AtomicTechnique(
            id="T0001", name="Multi", tactic="discovery", technique="T",
            platforms=[Platform.LINUX, Platform.WINDOWS], description="T",
            tests=[
                AtomicTest(name="linux-only", command="uname", platforms=[Platform.LINUX]),
                AtomicTest(name="win-only", command="hostname", executor="powershell", platforms=[Platform.WINDOWS]),
            ],
        )
        linux_tests = t.tests_for_platform("linux")
        assert len(linux_tests) == 1
        assert linux_tests[0].name == "linux-only"

        win_tests = t.tests_for_platform("windows")
        assert len(win_tests) == 1
        assert win_tests[0].name == "win-only"

    def test_no_tests_for_unsupported_platform(self):
        t = AtomicTechnique(
            id="T0001", name="Linux Only", tactic="discovery", technique="T",
            platforms=[Platform.LINUX], description="T",
            tests=[AtomicTest(name="linux", command="echo", platforms=[Platform.LINUX])],
        )
        assert t.tests_for_platform("windows") == []

    def test_test_platforms_field_optional(self):
        test = AtomicTest(name="test", command="echo")
        assert test.platforms is None

    def test_test_with_powershell_executor(self):
        test = AtomicTest(
            name="win test", command="Get-Date",
            executor="powershell", platforms=[Platform.WINDOWS],
        )
        assert test.executor == "powershell"
        assert test.platforms == [Platform.WINDOWS]
