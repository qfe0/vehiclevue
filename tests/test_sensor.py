"""Tests for sensor.py — VehicleSensor and platform setup."""
import logging
import pytest
from unittest.mock import MagicMock

from custom_components.vehiclevue.sensor import VehicleSensor, async_setup_entry
from custom_components.vehiclevue.const import DOMAIN, VUE_DATA
from tests.conftest import MOCK_GID


# ---------------------------------------------------------------------------
# VehicleSensor — construction and initial state
# ---------------------------------------------------------------------------

def test_initial_state(mock_vehicle, mock_vue):
    sensor = VehicleSensor(mock_vue, mock_vehicle)
    assert sensor.battery_level is None
    assert sensor.extra_attributes == {}


# ---------------------------------------------------------------------------
# VehicleSensor — async_update
# ---------------------------------------------------------------------------

async def test_async_update_populates_battery(mock_vehicle, mock_vue):
    sensor = VehicleSensor(mock_vue, mock_vehicle)
    await sensor.async_update()
    assert sensor.native_value == 75


async def test_async_update_populates_extra_attrs(mock_vehicle, mock_vue, mock_vehicle_status):
    sensor = VehicleSensor(mock_vue, mock_vehicle)
    await sensor.async_update()
    assert sensor.extra_state_attributes == mock_vehicle_status.as_dictionary.return_value


async def test_async_update_failure_does_not_crash(mock_vehicle, mock_vue, caplog):
    mock_vue.get_vehicle_status.side_effect = RuntimeError("API down")
    sensor = VehicleSensor(mock_vue, mock_vehicle)

    with caplog.at_level(logging.WARNING, logger="custom_components.vehiclevue.sensor"):
        await sensor.async_update()

    # State is unchanged from initial values.
    assert sensor.battery_level is None
    assert sensor.extra_attributes == {}
    # The warning branch actually executed.
    assert "Failed to update vehicle" in caplog.text


# ---------------------------------------------------------------------------
# VehicleSensor — properties
# ---------------------------------------------------------------------------

def test_name_property(mock_vehicle, mock_vue):
    sensor = VehicleSensor(mock_vue, mock_vehicle)
    assert sensor.name == "Test EV"


def test_unique_id_property(mock_vehicle, mock_vue):
    sensor = VehicleSensor(mock_vue, mock_vehicle)
    assert sensor.unique_id == "sensor.vehiclevue.123"


def test_device_info_property(mock_vehicle, mock_vue):
    sensor = VehicleSensor(mock_vue, mock_vehicle)
    info = sensor.device_info
    assert (DOMAIN, 123) in info["identifiers"]
    assert info["name"] == "Test EV"


# ---------------------------------------------------------------------------
# sensor.async_setup_entry — platform wiring
# ---------------------------------------------------------------------------

async def test_sensor_async_setup_entry_registers_sensors(hass, mock_vehicle, mock_vue):
    """async_setup_entry reads vue from hass.data and registers one sensor per vehicle."""
    from homeassistant.config_entries import ConfigEntry

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {VUE_DATA: mock_vue}

    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)

    async_add_entities.assert_called_once()
    sensors = async_add_entities.call_args[0][0]
    assert len(sensors) == 1
    assert isinstance(sensors[0], VehicleSensor)
    assert sensors[0].vehicle is mock_vehicle
