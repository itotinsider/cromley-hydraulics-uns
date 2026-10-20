"""Shared setup: import paths, the committed inventory and the code-generated one."""

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("common", "tools"):
    p = os.path.join(ROOT, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

SEED = int(os.environ.get("CH_TEST_SEED", "1"))
LAYERS = ("customer", "commands", "ch", "hardwired", "scenarios", "api")


def read(rel_path):
    with open(os.path.join(ROOT, rel_path), encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="session")
def inv():
    """The committed inventory (the contract)."""
    return {name: json.loads(read(f"inventory/{name}.json")) for name in LAYERS}


@pytest.fixture(scope="session")
def code():
    """The same, generated from the code as it is now (so contract tests don't depend on regenerating)."""
    import inventory
    return {n[:-5]: json.loads(t) for n, t in inventory.build().items() if n.endswith(".json")}


@pytest.fixture(scope="session")
def models():
    """(dam model module, CH model module, offline_sim module)."""
    import offline_sim
    return offline_sim.dam_model, offline_sim.ch_model, offline_sim
