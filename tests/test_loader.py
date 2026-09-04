import pytest

from halberd.library.loader import (
    load_all_atomics,
    load_all_chains,
    load_atomic,
    load_chain,
    validate_chain_references,
    get_technique_index,
)


class TestLoader:
    def test_load_all_atomics(self):
        techniques = load_all_atomics()
        assert len(techniques) >= 15
        ids = {t.id for t in techniques}
        assert "T1082" in ids
        assert "T1048.001" in ids

    def test_load_single_atomic(self):
        t = load_atomic("T1082")
        assert t.name == "System Information Discovery"
        assert len(t.tests) >= 1

    def test_load_missing_atomic(self):
        with pytest.raises(FileNotFoundError):
            load_atomic("T9999.999")

    def test_load_all_chains(self):
        chains = load_all_chains()
        assert len(chains) >= 3
        ids = {c.id for c in chains}
        assert "chain-dns-exfil" in ids

    def test_load_single_chain(self):
        c = load_chain("chain-dns-exfil")
        assert "exfiltration" in c.mitre_tactics

    def test_validate_chain_references(self):
        c = load_chain("chain-dns-exfil")
        missing = validate_chain_references(c)
        assert len(missing) == 0

    def test_technique_index(self):
        index = get_technique_index()
        assert isinstance(index, dict)
        assert "T1082" in index
