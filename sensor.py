""" Support for HomeAssistant Sensor (Temperature). """
# from var_dump import var_dump

from homeassistant.components.sensor import (SensorEntity)
from homeassistant.const import STATE_OFF, STATE_ON

from .const import (_LOGGER, DOMAIN)
from .gateway import get_gateway_from_config_entry
from .util import get_key_for_word, get_element_from_list



async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Component doesn't support configuration through configuration.yaml."""
    return


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Temperature Sensor for OpenMotics Controller."""
    gateway = get_gateway_from_config_entry(hass, config_entry)

    entities = []
    om_sensor_temperature = []
    om_sensor_humidity = []
    om_rooms = gateway.get_om_rooms()

    for sensor in gateway.get_om_sensor_temperature():
        if sensor['physical_quantity'] == 'temperature':
            sensor['floor'] = get_element_from_list(om_rooms, "id", sensor['room'])
            om_sensor_temperature.append(sensor)

    if not om_sensor_temperature:
        _LOGGER.debug("No temperature sensor found.")
        return False

    for entity in om_sensor_temperature:
        _LOGGER.debug("Adding temperature sensor %s", entity)
        entities.append(OpenMoticsTemperature(hass, gateway, entity))

    if not entities:
        _LOGGER.warning("No OpenMotics Temperature Sensors added")
        return False

    async_add_entities(entities)

class OpenMoticsTemperature(SensorEntity):
    """Representation of a OpenMotics temperature sensor."""

    def __init__(self, hass, gateway, sensor):
        """Initialize the sensor."""
        self._hass = hass
        self.gateway = gateway
        self._id = sensor['id']
        self._external_id = sensor['external_id']
        self._name = sensor['name']
        self._floor = sensor['floor']
        self._room = sensor['room']
        self._physical_quantity = sensor['physical_quantity']
        self._virtual = sensor['virtual']
        self._offset = sensor['offset']
        self._unit = sensor['unit']
        self._value = None

        self._refresh()

    @property
    def supported_features(self):
        """Flag supported features."""

        return 0

    # @property
    # def should_poll(self):
    #     """Enable polling."""
    #     return True

    @property
    def name(self):
        """Return the name of the temperature sensor."""
        return self._name

    @property
    def floor(self):
        """Return the floor of the temperature sensor."""
        return self._floor

    @property
    def room(self):
        """Return the room of the temperature sensor."""
        return self._room

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._id

    @property
    def native_unit_of_measurement(self):
        """Return native_unit_of_measurement of the temperature sensor."""
        return self._unit

    @property
    def unit_of_measurement(self):
        """Return unit_of_measurement of the temperature sensor."""
        return self._unit

    @property
    def native_value(self):
        """Return native_value of the temperature sensor."""
        return self._value

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

    @property
    def available(self):
        """If sensor is available."""
        return self._name is not None

    async def async_update(self):
        """Retrieve latest state."""
        await self._hass.async_add_executor_job(self._refresh)

    def _refresh(self):
        """Refresh the state of the temperature sensor."""
        sensor_temperature_status = self.gateway.get_sensor_temperature_status(self._id)

        if sensor_temperature_status is None:
            _LOGGER.debug("Temperature._refresh: Gateway not available. (%s = %s)", self._id, self._value)
            return

        _LOGGER.debug("Temperature._refresh: %s = %s", self._name, self._value)

        self._value = sensor_temperature_status
