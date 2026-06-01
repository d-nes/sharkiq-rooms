from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import CONF_EUROPE, DOMAIN, PLATFORMS
from sharkiq.ayla_api import get_ayla_api
from sharkiq.exc import SharkIqAuthError


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    api = get_ayla_api(
        entry.data["email"],
        entry.data["password"],
        europe=entry.data.get(CONF_EUROPE, False),
    )

    # Authenticate now so platform setup can fetch devices.
    try:
        await api.async_sign_in()
    except SharkIqAuthError as err:
        raise ConfigEntryAuthFailed("Invalid SharkIQ credentials") from err
    except Exception as err:
        # Transient/network issue - ask HA to retry later
        raise ConfigEntryNotReady from err

    hass.data[DOMAIN][entry.entry_id] = {"api": api}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register an integration-level service to send the robot to a named room.
    from homeassistant.helpers import config_validation as cv
    import voluptuous as vol

    async def _handle_clean_room(call):
        room_name = call.data.get("room_name")
        entity_ids = call.data.get("entity_id")
        if entity_ids:
            # Delegate to vacuum entity service for the provided entity ids
            for eid in entity_ids:
                await hass.services.async_call(
                    "vacuum",
                    "clean_room",
                    {"entity_id": eid, "room_name": room_name},
                    blocking=True,
                )
        else:
            # No entity specified: call vacuum.clean_room on all vacuum entities.
            all_vac = [s.entity_id for s in hass.states.async_all("vacuum")]
            for eid in all_vac:
                await hass.services.async_call(
                    "vacuum",
                    "clean_room",
                    {"entity_id": eid, "room_name": room_name},
                    blocking=True,
                )

    hass.services.async_register(
        DOMAIN,
        "clean_room",
        _handle_clean_room,
        schema=vol.Schema({vol.Required("room_name"): str, vol.Optional("entity_id"): cv.entity_ids}),
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        api = hass.data[DOMAIN].pop(entry.entry_id)
        try:
            await api["api"].async_close_session()
        except Exception:
            pass
    return unload_ok
