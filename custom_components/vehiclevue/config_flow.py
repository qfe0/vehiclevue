"""Config flow for Emporia Vue integration."""
import logging
import asyncio
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import AbortFlow

from pyemvue import PyEmVue

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    vue = PyEmVue()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, vue.login, data[CONF_EMAIL], data[CONF_PASSWORD])
    if not result:
        raise InvalidAuth

    # Return tokens only — do not persist the password.
    return {
        "title": f"Emporia User {data[CONF_EMAIL]}",
        "gid": str(vue.customer.customer_gid),
        CONF_EMAIL: data[CONF_EMAIL],
        "id_token": vue.auth.id_token,
        "access_token": vue.auth.access_token,
        "refresh_token": vue.auth.refresh_token,
    }


class ConfigFlow(config_entries.ConfigFlow, domain="vehiclevue"):
    """Handle a config flow for Emporia Vue settings."""

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                await self.async_set_unique_id(info["gid"])
                self._abort_if_unique_id_configured()
                # Store the token dict, not raw user_input (no password persisted).
                return self.async_create_entry(title=info["title"], data=info)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except AbortFlow:
                raise
            except Exception as err:
                _LOGGER.error("Unexpected vehiclevue setup error: %s", type(err).__name__)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data):
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Handle re-authentication confirmation."""
        errors = {}
        existing_entry = self._get_reauth_entry()
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                await self.async_set_unique_id(info["gid"])
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    existing_entry,
                    data_updates={k: v for k, v in info.items() if k != "title"},
                )
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except AbortFlow:
                raise
            except Exception as err:
                _LOGGER.error("Unexpected vehiclevue reauth error: %s", type(err).__name__)
                errors["base"] = "unknown"
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
