import pytest
from unittest.mock import MagicMock
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

MOCK_EMAIL = "test@example.com"
MOCK_PASSWORD = "hunter2"
MOCK_GID = "42"
MOCK_ID_TOKEN = "id_tok"
MOCK_ACCESS_TOKEN = "acc_tok"
MOCK_REFRESH_TOKEN = "ref_tok"

TOKEN_ENTRY_DATA = {
    CONF_EMAIL: MOCK_EMAIL,
    "gid": MOCK_GID,
    "id_token": MOCK_ID_TOKEN,
    "access_token": MOCK_ACCESS_TOKEN,
    "refresh_token": MOCK_REFRESH_TOKEN,
}

LEGACY_ENTRY_DATA = {
    CONF_EMAIL: MOCK_EMAIL,
    CONF_PASSWORD: MOCK_PASSWORD,
    "gid": MOCK_GID,
}


@pytest.fixture
def mock_vehicle():
    v = MagicMock()
    v.vehicle_gid = 123
    v.display_name = "Test EV"
    return v


@pytest.fixture
def mock_vehicle_status():
    s = MagicMock()
    s.battery_level = 75
    s.as_dictionary.return_value = {"battery_level": 75, "charge_status": "charging"}
    return s


@pytest.fixture
def mock_vue(mock_vehicle, mock_vehicle_status):
    vue = MagicMock()
    vue.customer.customer_gid = int(MOCK_GID)
    vue.auth.id_token = MOCK_ID_TOKEN
    vue.auth.access_token = MOCK_ACCESS_TOKEN
    vue.auth.refresh_token = MOCK_REFRESH_TOKEN
    vue.login.return_value = True
    vue.get_vehicles.return_value = [mock_vehicle]
    vue.get_vehicle_status.return_value = mock_vehicle_status
    return vue
