from board_agent.probes import get_resources, get_system_info


def test_mock_system_info_matches_board_baseline():
    info = get_system_info(mock=True)

    assert info.hostname == "rk3568-mock"
    assert info.arch == "aarch64"
    assert "4.19.232" in info.kernel


def test_mock_resources_match_known_board_devices():
    resources = get_resources(mock=True)

    assert "/dev/gpiochip0" in resources.gpiochips
    assert "/dev/i2c-5" in resources.i2c_buses
    assert "/dev/ttyS7" in resources.serial_ports
    assert "can0" in resources.can_interfaces
    assert resources.mode == "mock"
