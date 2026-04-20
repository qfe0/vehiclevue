"""The Emporia Vue integration."""
import asyncio
import logging
import voluptuous as vol

from pyemvue import PyEmVue

from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, VUE_DATA

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = ["sensor"]

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):

    hass.data.setdefault(DOMAIN, {})
    conf = config.get(DOMAIN)
    if not conf:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={
                CONF_EMAIL: conf[CONF_EMAIL],
                CONF_PASSWORD: conf[CONF_PASSWORD],
            },
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Emporia Vue from a config entry."""
    entry_data = entry.data
    email = entry_data[CONF_EMAIL]

    _LOGGER.info("Setting up Vue client for user %s", email)

    vue = PyEmVue(read_timeout=12)
    loop = asyncio.get_running_loop()
    try:
        if entry_data.get("id_token"):
            # Token-based auth — password is not stored in the config entry.
            result = await loop.run_in_executor(
                None, vue.login,
                None, None,
                entry_data["id_token"],
                entry_data["access_token"],
                entry_data["refresh_token"],
            )
        elif entry_data.get(CONF_PASSWORD):
            # Legacy entry created before the token migration — authenticate once
            # with the stored password, then update the entry to store tokens only.
            result = await loop.run_in_executor(
                None, vue.login, email, entry_data[CONF_PASSWORD]
            )
            if result:
                hass.config_entries.async_update_entry(
                    entry,
                    data={
                        CONF_EMAIL: email,
                        "gid": entry_data.get("gid", ""),
                        "id_token": vue.auth.id_token,
                        "access_token": vue.auth.access_token,
                        "refresh_token": vue.auth.refresh_token,
                    },
                )
        else:
            raise ConfigEntryAuthFailed("No credentials available — please re-authenticate")

        if not result:
            raise ConfigEntryAuthFailed("Emporia authentication failed")
        _LOGGER.debug("Logged in %s", email)
    except ConfigEntryAuthFailed:
        raise
    except Exception as err:
        _LOGGER.warning("vehiclevue auth failed: %s", type(err).__name__)
        raise ConfigEntryAuthFailed("Emporia authentication failed") from err

    try:
        result = await loop.run_in_executor(None, vue.get_vehicles)
        if len(result) == 0:
            raise Exception("No vehicles configured in Emporia account.")
    except Exception as err:
        _LOGGER.error("No vehicles configured in Emporia account: %s", type(err).__name__)
        return False

    hass.data[DOMAIN][entry.entry_id] = {
        VUE_DATA: vue
    }

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception as err:
        _LOGGER.error("Error setting up platforms: %s", err)
        raise ConfigEntryNotReady(f"Error setting up platforms: {err}")

    return True
