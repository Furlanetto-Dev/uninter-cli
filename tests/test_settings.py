import pytest
from doubles import SettingsWithoutEnvFile
from pydantic import ValidationError


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
def test_the_mcp_listens_on_loopback(host: str) -> None:
    assert SettingsWithoutEnvFile(mcp_host=host).mcp_host == host


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.0.10"])
def test_any_other_mcp_host_is_refused_saying_why(host: str) -> None:
    with pytest.raises(ValidationError, match="não tem token"):
        SettingsWithoutEnvFile(mcp_host=host)
