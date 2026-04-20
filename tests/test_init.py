"""Tests for __init__.py — async_setup and async_setup_entry paths."""
import pytest
from unittest.mock import patch, AsyncMock
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.exceptions import ConfigEntryAuthFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vehiclevue import async_setup, async_setup_entry
from custom_components.vehiclevue.const import DOMAIN, VUE_DATA
from tests.conftest import (
    MOCK_EMAIL, MOCK_PASSWORD, MOCK_GID,
    MOCK_ID_TOKEN, MOCK_ACCESS_TOKEN, MOCK_REFRESH_TOKEN,
    TOKEN_ENTRY_DATA, LEGACY_ENTRY_DATA,
)

PATCH_VUE = "custom_components.vehiclevue.PyEmVue"
# Patch async_forward_entry_setups so __init__ unit tests don't cascade into
# the sensor platform — sensor.async_setup_entry is tested separately.
PATCH_FWD = "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups"


def _token_entry(hass):
    e = MockConfigEntry(domain=DOMAIN, data=TOKEN_ENTRY_DATA, unique_id=MOCK_GID)
    e.add_to_hass(hass)
    return e


# ---------------------------------------------------------------------------
# async_setup (YAML import path)
# ---------------------------------------------------------------------------

async def test_yaml_import_schedules_flow(hass):
    config = {DOMAIN: {CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: MOCK_PASSWORD}}
    result = await async_setup(hass, config)

    assert result is True
    assert DOMAIN in hass.data


async def test_yaml_import_empty_config_returns_true(hass):
    result = await async_setup(hass, {})
    assert result is True


# ---------------------------------------------------------------------------
# async_setup_entry — auth branches
# ---------------------------------------------------------------------------

async def test_token_auth_success(hass, mock_vue):
    hass.data.setdefault(DOMAIN, {})
    entry = _token_entry(hass)

    with patch(PATCH_VUE, return_value=mock_vue), \
         patch(PATCH_FWD, new=AsyncMock(return_value=True)):
        result = await async_setup_entry(hass, entry)

    assert result is True
    assert hass.data[DOMAIN][entry.entry_id][VUE_DATA] is mock_vue
    # Verify the token branch was taken, not the password branch.
    mock_vue.login.assert_called_once_with(
        None, None, MOCK_ID_TOKEN, MOCK_ACCESS_TOKEN, MOCK_REFRESH_TOKEN
    )


async def test_token_auth_login_false_raises_auth_failed(hass, mock_vue):
    hass.data.setdefault(DOMAIN, {})
    entry = _token_entry(hass)
    mock_vue.login.return_value = False

    with patch(PATCH_VUE, return_value=mock_vue), \
         pytest.raises(ConfigEntryAuthFailed):
        await async_setup_entry(hass, entry)


async def test_token_auth_exception_raises_auth_failed(hass, mock_vue):
    hass.data.setdefault(DOMAIN, {})
    entry = _token_entry(hass)
    mock_vue.login.side_effect = RuntimeError("connection refused")

    with patch(PATCH_VUE, return_value=mock_vue), \
         pytest.raises(ConfigEntryAuthFailed):
        await async_setup_entry(hass, entry)


async def test_legacy_password_migrates_to_tokens(hass, mock_vue):
    """Entry with stored password is re-authed once and entry is updated to tokens."""
    hass.data.setdefault(DOMAIN, {})
    entry = MockConfigEntry(domain=DOMAIN, data=LEGACY_ENTRY_DATA, unique_id=MOCK_GID)
    entry.add_to_hass(hass)

    with patch(PATCH_VUE, return_value=mock_vue), \
         patch(PATCH_FWD, new=AsyncMock(return_value=True)):
        result = await async_setup_entry(hass, entry)

    assert result is True
    assert CONF_PASSWORD not in entry.data
    assert entry.data["id_token"] == MOCK_ID_TOKEN


async def test_no_credentials_raises_auth_failed(hass, mock_vue):
    hass.data.setdefault(DOMAIN, {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: MOCK_EMAIL},  # no tokens, no password
        unique_id=MOCK_GID,
    )
    entry.add_to_hass(hass)

    with patch(PATCH_VUE, return_value=mock_vue), \
         pytest.raises(ConfigEntryAuthFailed):
        await async_setup_entry(hass, entry)


# ---------------------------------------------------------------------------
# async_setup_entry — post-auth branches
# ---------------------------------------------------------------------------

async def test_no_vehicles_returns_false(hass, mock_vue):
    hass.data.setdefault(DOMAIN, {})
    entry = _token_entry(hass)
    mock_vue.get_vehicles.return_value = []

    with patch(PATCH_VUE, return_value=mock_vue):
        result = await async_setup_entry(hass, entry)

    assert result is False
