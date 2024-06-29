""" Support for HomeAssistant lights. """
# from var_dump import var_dump

from homeassistant.components.light import (ATTR_BRIGHTNESS,
                                            SUPPORT_BRIGHTNESS, LightEntity)
from homeassistant.const import STATE_OFF, STATE_ON

from typing import Final

from .const import (_LOGGER, DOMAIN, OPENMOTICS_MODULE_TYPE_TO_NAME,
                    OPENMOTICS_OUTPUT_TYPE_TO_NAME)
from .gateway import get_gateway_from_config_entry
from .util import get_key_for_word, get_element_from_list

TURN_ON: Final = "turn_on"
TURN_OFF: Final = "turn_off"

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Component doesn't support configuration through configuration.yaml."""
    return


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Lights for OpenMotics Controller."""
    gateway = get_gateway_from_config_entry(hass, config_entry)
    coordinator = hass.data[DOMAIN].get('coordinator')

    _LOGGER.debug("Light: here.")

    entities = []
    om_lights = []
    om_rooms = gateway.get_om_rooms()

    light_type = get_key_for_word(OPENMOTICS_OUTPUT_TYPE_TO_NAME, 'light')
    for module in gateway.get_om_output_modules():
        if module['type'] == light_type:
            module['floor'] = get_element_from_list(om_rooms, "id", module['room'])
            om_lights.append(module)

    if not om_lights:
        _LOGGER.debug("No lights found.")
        return False

    for entity in om_lights:
        _LOGGER.debug("Adding light %s", entity)
        entities.append(OpenMoticsLight(hass, coordinator, idx, gateway, entity) for idx, ent in enumerate(coordinator.data))

    if not entities:
        _LOGGER.warning("No OpenMotics Lights added")
        return False

    async_add_entities(entities)


def brightness_to_percentage(byt):
    """Convert brightness from absolute 0..255 to percentage."""
    return round((byt * 100.0) / 255.0)


def brightness_from_percentage(percent):
    """Convert percentage to absolute value 0..255."""
    return round((percent * 255.0) / 100.0)


class OpenMoticsLight(CoordinatorEntity, LightEntity):
    """Representation of a OpenMotics light."""

    def __init__(self, hass, coordinator, idx, gateway, light):
        """Initialize the light."""
        super().__init__(coordinator)
        self._hass = hass
        self.idx = idx
        self.gateway = gateway
        self._id = light['id']
        self._name = light['name']
        self._floor = light['floor']
        self._room = light['room']
        self._module_type = light['module_type']
        self._type = light['type']
        self._timer = None
        self._dimmer = None
        self._state = None
        self._event = None

        #self._refresh()

    @property
    def supported_features(self):
        """Flag supported features."""
        # Check if the light's module is a Dimmer, return brightness as a supported feature.
        if self._module_type == get_key_for_word(OPENMOTICS_MODULE_TYPE_TO_NAME, 'Dimmer'):
            return SUPPORT_BRIGHTNESS

        return 0

    #@property
    #def should_poll(self):
    #    """Enable polling."""
    #    return True

    @property
    def name(self):
        """Return the name of the light."""
        return self._name

    @property
    def floor(self):
        """Return the floor of the light."""
        return self._floor

    @property
    def room(self):
        """Return the room of the light."""
        return self._room

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._id

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.coordinator.data[self.idx]["_state"] == STATE_ON
        #return self._state == STATE_ON

    @property
    def device_info(self):
        """Return information about the device."""
        info = {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "id": self.unique_id,
            "floor": self.floor,
            "room": self.room,
            "manufacturer": "OpenMotics",
        }
        return info

    #@property
    #def available(self):
    #    """If light is available."""
    #    return self._state is not None

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        # brightness = int(self._dimmer * BRIGHTNESS_SCALE_UP)
        # :type dimmer: Integer [0, 100] or None
        if self._dimmer is None:
            return 0

        return brightness_from_percentage(self._dimmer)

    async def async_turn_on(self, **kwargs):
        """Turn device on."""
        brightness = 0
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
        else:
            if self._dimmer is not None:
                brightness = brightness_from_percentage(self._dimmer)
            if brightness == 0:
                brightness = 255

        self._dimmer = brightness_to_percentage(brightness)

        self._event = TURN_ON

        sop = await self._hass.async_add_executor_job(self.gateway.api.set_output, self._id, True, self._dimmer, self._timer)
        _LOGGER.debug("Light._turn_on %s", self._state)
        if sop['success'] is True:
            self._state = STATE_ON
        else:
            _LOGGER.error("Error setting output id %s to True", self._id)
            self._state = STATE_OFF
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn devicee off."""
        self._event = TURN_OFF

        sop = await self._hass.async_add_executor_job(self.gateway.api.set_output, self._id, False, None, None)
        _LOGGER.debug("Light._turn_off %s", self._state)
        if sop['success'] is True:
            self._state = STATE_OFF
        else:
            _LOGGER.error("Error setting output id %s to False", self._id)
            self._state = STATE_ON

        await self.coordinator.async_request_refresh()

    #async def async_update(self):
    #    """Retrieve latest state."""
    #    await self._hass.async_add_executor_job(self._refresh)

    #def _refresh(self):
    #    """Refresh the state of the light."""
    #    _LOGGER.debug("Light._refresh: %s (%s) = %s (before)", self._name, self._id, self._state)

    #    self.gateway.update

    #    if self._event is not None:
    #        _LOGGER.debug("Light._event: local event %s = %s", self._name, self._state)
    #        self._event = None
    #        return

    #    output_status = self.gateway.get_output_status(self._id)
        # {'status': 1, 'dimmer': 100, 'ctimer': 0, 'id': 66}

    #    _LOGGER.debug("Light._refresh: %s (%s) output_status = %s", self._name, self._id, output_status)

    #    if not output_status:
    #        _LOGGER.error('Light._refresh: No response from the controller')
    #        return

    #    if output_status['dimmer'] is not None:
    #        self._dimmer = output_status['dimmer']

    #    if output_status['ctimer'] is not None:
    #        self._ctimer = output_status['ctimer']

    #    if output_status['status'] is not None:
    #        if output_status['status'] == 1:
    #            self._state = STATE_ON
    #        else:
    #            self._state = STATE_OFF
    #    else:
    #        self._state = None

    #    _LOGGER.debug("Light._refresh: %s (%s) = %s", self._name, self._id, self._state)