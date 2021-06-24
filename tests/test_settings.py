import copy
from sacred import SETTINGS as DEFAULT_SETTINGS

import pytest

from sacred.settings import SettingError


def test_access_invalid_setting():
    SETTINGS = copy.deepcopy(DEFAULT_SETTINGS)
    with pytest.raises(SettingError):
        SETTINGS.INVALID_SETTING = "invalid"
    with pytest.raises(SettingError):
        SETTINGS["INVALID_SETTING"] = "invalid"


def test_overwrite_collection():
    SETTINGS = copy.deepcopy(DEFAULT_SETTINGS)
    with pytest.raises(SettingError):
        SETTINGS.CONFIG = "invalid"
    with pytest.raises(SettingError):
        SETTINGS["CONFIG"] = "invalid"


def test_access_valid_setting():
    SETTINGS = copy.deepcopy(DEFAULT_SETTINGS)
    SETTINGS.CONFIG.READ_ONLY_CONFIG = True
    assert SETTINGS.CONFIG.READ_ONLY_CONFIG
