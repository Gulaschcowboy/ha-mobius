"""Replacement-gateway choice: prefer members known to cover the most members,
rank members that failed as gateway themselves worst."""
from unittest.mock import MagicMock

from custom_components.mobius.gateway_registry import GatewayRegistry, PanGroup


def _group(*serials):
    group = PanGroup(pan_id=1)
    group.members = {serial: MagicMock() for serial in serials}
    return group


def test_failed_as_gateway_ranks_worst():
    group = _group("a", "b", "c")
    group.failed_as_gateway.add("c")
    assert GatewayRegistry._badness(group, "c") == 3
    assert GatewayRegistry._badness(group, "a") == 0


def test_worse_than_best_keeps_only_best_known():
    group = _group("a", "b", "c", "d")
    group.unpollable_via = {"a": {"x"}, "b": {"x", "y"}}
    group.failed_as_gateway.add("d")
    registry = GatewayRegistry.__new__(GatewayRegistry)
    # c is untried (0) -> best; a, b, d are worse
    assert registry._worse_than_best(group, set()) == {"a", "b", "d"}
    # with c excluded, a (1 failure) is best
    assert registry._worse_than_best(group, {"c"}) == {"b", "d"}
    assert registry._worse_than_best(group, {"a", "b", "c", "d"}) == set()


def test_covers_no_better_counts_failed_as_gateway():
    group = _group("a", "b", "c")
    group.unpollable_via = {"a": {"b"}}
    group.failed_as_gateway.add("c")
    registry = GatewayRegistry.__new__(GatewayRegistry)
    assert registry._covers_no_better(group, "a") == {"a", "c"}
