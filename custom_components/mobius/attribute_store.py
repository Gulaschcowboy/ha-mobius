"""
Supported attribute tables kept across Home Assistant restarts.

Reading a device's supported attribute table is the largest read the
integration makes. Over a relay it often times out. The Mobius app reads the
table once and keeps it with the device: it reads it again only when the table
is missing, after a firmware update, or when a read reports an unsupported
attribute. This module does the same, keyed by serial. A table that changed
on the device is detected by the poll (SupportedAttributesCRC) and dropped
here, so the next poll reads it again.
"""

from __future__ import annotations

from typing import Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.supported_attributes"
_DATA_KEY = f"{DOMAIN}_supported_attributes_store"
SAVE_DELAY = 10


async def _async_load(hass: HomeAssistant) -> tuple[Store, dict[str, list[int]]]:
    loaded = hass.data.get(_DATA_KEY)
    if loaded is None:
        store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        data = await store.async_load()
        if not isinstance(data, dict):
            data = {}
        # Another coordinator may have loaded it while this one awaited.
        loaded = hass.data.setdefault(_DATA_KEY, (store, data))
    return loaded


async def async_get(hass: HomeAssistant, serial: str) -> Optional[set[int]]:
    """The stored attribute ids of `serial`, or None if none are stored."""
    _store, data = await _async_load(hass)
    ids = data.get(serial)
    if not ids:
        return None
    return {int(i) for i in ids}


def _schedule_save(hass: HomeAssistant) -> None:
    store, data = hass.data[_DATA_KEY]
    store.async_delay_save(lambda: data, SAVE_DELAY)


async def async_set(hass: HomeAssistant, serial: str, ids: set[int]) -> None:
    _store, data = await _async_load(hass)
    data[serial] = sorted(ids)
    _schedule_save(hass)


@callback
def async_forget(hass: HomeAssistant, serial: str) -> None:
    """Drops the table of `serial` (it changed on the device)."""
    loaded = hass.data.get(_DATA_KEY)
    if loaded is None:
        return
    _store, data = loaded
    if data.pop(serial, None) is not None:
        _schedule_save(hass)
