import voluptuous as vol

# Vacuum entity location moved across HA versions; try actual vacuum platform imports first.
try:
    from homeassistant.components.vacuum import VacuumEntity
except Exception:
    try:
        from homeassistant.components.vacuum.entity import VacuumEntity
    except Exception:
        # Final fallback: use HA's base Entity so `entity_id` exists.
        from homeassistant.helpers.entity import Entity as VacuumEntity

# Vacuum supported features live in different places across HA versions.
try:
    from homeassistant.components.vacuum.const import VacuumEntityFeature
    SUPPORT_RETURN_HOME = VacuumEntityFeature.RETURN_HOME
    SUPPORT_SEND_COMMAND = VacuumEntityFeature.SEND_COMMAND
except Exception:
    try:
        from homeassistant.components.vacuum import (
            SUPPORT_RETURN_HOME,
            SUPPORT_SEND_COMMAND,
        )
    except Exception:
        SUPPORT_RETURN_HOME = 16
        SUPPORT_SEND_COMMAND = 256

from homeassistant.helpers import entity_platform

from .const import ATTR_ROOM_NAME, DOMAIN, SERVICE_CLEAN_ROOM


async def async_setup_entry(hass, entry, async_add_entities):
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    devices = await hass.async_add_executor_job(api.get_devices)

    entities = [SharkIqVacuumEntity(device) for device in devices]
    async_add_entities(entities, True)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_CLEAN_ROOM,
        {vol.Required(ATTR_ROOM_NAME): str},
        "async_clean_room",
    )


class SharkIqVacuumEntity(VacuumEntity):
    def __init__(self, shark):
        self._shark = shark
        self._attr_name = shark.name
        self._attr_unique_id = shark.serial_number
        self._attr_supported_features = SUPPORT_RETURN_HOME | SUPPORT_SEND_COMMAND

    @property
    def available(self):
        return True

    @property
    def supported_features(self):
        return self._attr_supported_features

    @property
    def extra_state_attributes(self):
        rooms = self._shark.get_room_list() or []
        return {"available_rooms": rooms}

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._shark.serial_number)},
            "name": self._shark.name,
            "manufacturer": "SharkNinja",
            "model": self._shark.oem_model_number,
        }

    async def async_update(self):
        await self.hass.async_add_executor_job(self._shark.update)

    async def async_return_to_base(self):
        await self.hass.async_add_executor_job(self._shark.set_operating_mode, "Return")

    async def async_clean_room(self, room_name: str):
        await self.hass.async_add_executor_job(self._shark.update)
        await self.hass.async_add_executor_job(self._shark.clean_rooms, [room_name])

    async def async_send_command(self, command, params=None):
        if isinstance(command, list) and command:
            command = command[0]

        room_name = None
        if params is None:
            params = {}
        if isinstance(params, dict):
            room_name = params.get("room_name") or params.get("room") or params.get("area")

        if not room_name and isinstance(command, str):
            # Allow command to be a room name directly.
            room_name = command

        if not room_name:
            raise ValueError("send_command requires room_name in params or the command should be the room name")

        await self.async_clean_room(room_name)
