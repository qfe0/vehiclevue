import pytest
from unittest.mock import MagicMock, create_autospec
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from pyemvue.auth import Auth
from pyemvue.customer import Customer
from pyemvue.device import Vehicle, VehicleStatus

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


def make_mock_auth(id_token=MOCK_ID_TOKEN, access_token=MOCK_ACCESS_TOKEN, refresh_token=MOCK_REFRESH_TOKEN):
    auth = create_autospec(Auth, instance=True)
    auth.tokens = {"id_token": id_token, "access_token": access_token, "refresh_token": refresh_token}
    return auth


@pytest.fixture
def mock_vehicle():
    v = create_autospec(Vehicle, instance=True)
    v.vehicle_gid = 123
    v.display_name = "Test EV"
    return v


@pytest.fixture
def mock_vehicle_status():
    s = create_autospec(VehicleStatus, instance=True)
    s.battery_level = 75
    s.as_dictionary.return_value = {"battery_level": 75, "charge_status": "charging"}
    return s


@pytest.fixture
def mock_vue(mock_vehicle, mock_vehicle_status):
    vue = MagicMock()
    customer = create_autospec(Customer, instance=True)
    customer.customer_gid = int(MOCK_GID)
    vue.customer = customer
    vue.auth = make_mock_auth()
    vue.login.return_value = True
    vue.get_vehicles.return_value = [mock_vehicle]
    vue.get_vehicle_status.return_value = mock_vehicle_status
    return vue
