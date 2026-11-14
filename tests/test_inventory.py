"""The committed inventory/ must match what the code generates.

A failure here is not necessarily a bug: it means an interface changed (a topic, command,
hardwired signal, scenario or HTTP route was added, renamed or removed). If that was intended,
regenerate the inventory and commit it with the change, so the PR shows the interface diff:

    docker compose run --rm tests python tools/inventory.py
"""

import pytest

import inventory


def test_inventory_is_up_to_date():
    diff = inventory.diff()
    if diff:
        shown = "\n".join(diff[:150]) + (f"\n... {len(diff) - 150} more diff lines" if len(diff) > 150 else "")
        pytest.fail("inventory/ differs from the code. If the interface change is intended, run\n"
                    "    docker compose run --rm tests python tools/inventory.py\n"
                    "and commit inventory/ with it.\n\n" + shown, pytrace=False)


def test_interface_version_is_raised_with_the_interface():
    """An interface change needs a new INTERFACE_VERSION: projects that pin a commit compare it."""
    import namespace as NS
    now = inventory.digest(inventory.build())
    if now != NS.INTERFACE_DIGEST:
        pytest.fail("The interface changed since INTERFACE_VERSION " + NS.INTERFACE_VERSION + " was set.\n"
                    "In common/namespace.py raise INTERFACE_VERSION (first number: rename, removal, changed\n"
                    "type or unit; second number: addition) and set\n"
                    f'    INTERFACE_DIGEST = "{now}"\n'
                    "then regenerate the inventory and say in the PR what changed.", pytrace=False)


def test_interface_version_format():
    import namespace as NS
    major, minor = NS.INTERFACE_VERSION.split(".")
    assert major.isdigit() and minor.isdigit()
