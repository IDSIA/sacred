import copy
from sacred import SETTINGS as DEFAULT_SETTINGS

import pytest


def test_access_invalid_setting():
    SETTINGS = copy.deepcopy(DEFAULT_SETTINGS)
    with pytest.raises(AttributeError):
        SETTINGS.INVALID_SETTING = "invalid"
    with pytest.raises(KeyError):
        SETTINGS["INVALID_SETTING"] = "invalid"


def test_overwrite_collection():
    SETTINGS = copy.deepcopy(DEFAULT_SETTINGS)
    with pytest.raises(AttributeError):
        SETTINGS.CONFIG = "invalid"
    with pytest.raises(KeyError):
        SETTINGS["CONFIG"] = "invalid"


def test_partial_update():
    # Setting a mapping should partially update
    SETTINGS = copy.deepcopy(DEFAULT_SETTINGS)
    keys = set(SETTINGS.CONFIG.keys())
    SETTINGS.CONFIG = {"READ_ONLY_CONFIG": "somevalue"}
    assert SETTINGS.CONFIG.READ_ONLY_CONFIG == "somevalue"

    # All other config keys should still be there
    assert keys == set(SETTINGS.CONFIG.keys())


def test_access_valid_setting():
    SETTINGS = copy.deepcopy(DEFAULT_SETTINGS)
    SETTINGS.CONFIG.READ_ONLY_CONFIG = True
    assert SETTINGS.CONFIG.READ_ONLY_CONFIG
