"""Replacement-gateway choice: prefer members known to cover the most members,
rank members that failed as gateway themselves worst."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

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


def test_unreachable_target_not_promoted_itself():
    """A member the gateway can't relay to is avoided as the next gateway."""
    group = _group("gw", "target", "other")
    group.gateway_serial = "gw"
    group.generation = 0
    group.lock = asyncio.Lock()
    group.restart_policy = MagicMock(enabled=False)
    for member in group.members.values():
        member.consecutive_relay_failures = 0
        member.is_recovering = MagicMock(return_value=False)
    registry = GatewayRegistry.__new__(GatewayRegistry)
    registry._groups = {1: group}
    registry._promote_away_from_current_gateway = AsyncMock()

    async def run():
        for _ in range(3):
            await registry.record_relay_failure(1, "target", 0)

    asyncio.run(run())
    registry._promote_away_from_current_gateway.assert_awaited_once()
    assert registry._promote_away_from_current_gateway.await_args.kwargs["avoid"] == {"target"}
