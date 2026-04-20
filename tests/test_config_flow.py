"""Tests for config_flow.py — all meaningful paths through setup and reauth."""
import pytest
from unittest.mock import MagicMock, patch
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vehiclevue.const import DOMAIN
from tests.conftest import (
    MOCK_EMAIL, MOCK_PASSWORD, MOCK_GID,
    MOCK_ID_TOKEN, MOCK_ACCESS_TOKEN, MOCK_REFRESH_TOKEN,
    TOKEN_ENTRY_DATA,
)

PATCH_VUE = "custom_components.vehiclevue.config_flow.PyEmVue"
USER_INPUT = {CONF_EMAIL: MOCK_EMAIL, CONF_PASSWORD: MOCK_PASSWORD}


def _mock_vue(login_result=True):
    vue = MagicMock()
    vue.customer.customer_gid = int(MOCK_GID)
    vue.auth.id_token = MOCK_ID_TOKEN
    vue.auth.access_token = MOCK_ACCESS_TOKEN
    vue.auth.refresh_token = MOCK_REFRESH_TOKEN
    vue.login.return_value = login_result
    return vue


async def _start_user_flow(hass):
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})


# ---------------------------------------------------------------------------
# async_step_user
# ---------------------------------------------------------------------------

async def test_shows_form_on_get(hass):
    result = await _start_user_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_success_stores_tokens_not_password(hass):
    with patch(PATCH_VUE, return_value=_mock_vue()):
        r = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(r["flow_id"], USER_INPUT)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert CONF_PASSWORD not in result["data"]
    assert result["data"]["id_token"] == MOCK_ID_TOKEN
    assert result["data"]["access_token"] == MOCK_ACCESS_TOKEN


async def test_success_unique_id_set(hass):
    with patch(PATCH_VUE, return_value=_mock_vue()):
        r = await _start_user_flow(hass)
        await hass.config_entries.flow.async_configure(r["flow_id"], USER_INPUT)

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].unique_id == MOCK_GID


async def test_invalid_auth_shows_error(hass):
    with patch(PATCH_VUE, return_value=_mock_vue(login_result=False)):
        r = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(r["flow_id"], USER_INPUT)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_unexpected_exception_shows_unknown(hass):
    vue = MagicMock()
    vue.login.side_effect = RuntimeError("network down")
    with patch(PATCH_VUE, return_value=vue):
        r = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(r["flow_id"], USER_INPUT)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"


async def test_duplicate_account_aborts(hass):
    with patch(PATCH_VUE, return_value=_mock_vue()):
        r1 = await _start_user_flow(hass)
        await hass.config_entries.flow.async_configure(r1["flow_id"], USER_INPUT)

        r2 = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(r2["flow_id"], USER_INPUT)

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# async_step_reauth / async_step_reauth_confirm
# ---------------------------------------------------------------------------

async def _start_reauth_flow(hass, entry):
    """Initialize a reauth flow the way HA does — with source and entry_id context."""
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )


async def test_reauth_shows_form(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=TOKEN_ENTRY_DATA, unique_id=MOCK_GID)
    entry.add_to_hass(hass)

    result = await _start_reauth_flow(hass, entry)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"


async def test_reauth_success_updates_entry(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=TOKEN_ENTRY_DATA, unique_id=MOCK_GID)
    entry.add_to_hass(hass)

    new_id_token = "new_id_tok"
    new_vue = _mock_vue()
    new_vue.auth.id_token = new_id_token

    with patch(PATCH_VUE, return_value=new_vue):
        r = await _start_reauth_flow(hass, entry)
        result = await hass.config_entries.flow.async_configure(r["flow_id"], USER_INPUT)

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["id_token"] == new_id_token
    assert CONF_PASSWORD not in entry.data
