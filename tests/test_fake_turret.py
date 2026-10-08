import pytest
import serial

from antenna_tracker.hardware.fake_turret import WARNING_LINE, FakeSerial, FakeTurretDevice


def lines(ser: FakeSerial) -> list[str]:
    out = []
    while (b := ser.readline()):
        out.append(b.decode().strip())
    return out


def cmd(ser: FakeSerial, text: str) -> list[str]:
    ser.write((text + "\n").encode())
    return lines(ser)


@pytest.fixture
def dev() -> FakeTurretDevice:
    return FakeTurretDevice()


@pytest.fixture
def ser(dev: FakeTurretDevice) -> FakeSerial:
    s = FakeSerial(device=dev, timeout=0.05)
    assert lines(s) == ["Turret Ready"]
    return s


def test_commands(ser: FakeSerial, dev: FakeTurretDevice) -> None:
    assert cmd(ser, "GET") == ["OK:90,90"]
    assert cmd(ser, "MOVE,100,120") == ["OK:100,120"]
    assert cmd(ser, "get") == ["OK:100,120"]
    assert cmd(ser, " init ") == ["OK:90,90"]
    assert dev.eeprom == [90, 90]


def test_limits(ser: FakeSerial) -> None:
    assert cmd(ser, "MOVE,4,90") == ["LIMIT"]
    assert cmd(ser, "MOVE,90,161") == ["LIMIT"]
    assert cmd(ser, "MOVE,30,150") == ["LIMIT"]
    assert cmd(ser, "MOVE,5,96") == ["LIMIT"]
    assert cmd(ser, "MOVE,5,95") == ["OK:5,95"]


def test_ignored_input(ser: FakeSerial) -> None:
    assert cmd(ser, "MOVE,90") == []
    assert cmd(ser, "HELLO") == []
    assert cmd(ser, "move,90,90") == []
    assert cmd(ser, "MOVE,abc,90") == ["LIMIT"]
    assert cmd(ser, "MOVE,95x,100") == ["OK:95,100"]


def test_eeprom_survives_power_cycle(ser: FakeSerial, dev: FakeTurretDevice) -> None:
    cmd(ser, "MOVE,120,100")
    dev.power_off()
    with pytest.raises(serial.SerialException):
        ser.write(b"GET\n")
    with pytest.raises(serial.SerialException):
        FakeSerial(device=dev)
    dev.power_on()
    s2 = FakeSerial(device=dev, timeout=0.05)
    assert lines(s2) == ["Turret Ready"]
    assert cmd(s2, "GET") == ["OK:120,100"]


def test_invalid_eeprom_defaults() -> None:
    s = FakeSerial(device=FakeTurretDevice(eeprom_pan=255, eeprom_tilt=255), timeout=0.05)
    assert lines(s) == ["Turret Ready"]
    assert cmd(s, "GET") == ["OK:90,90"]


def test_eeprom_box_valid_but_unreachable_warns() -> None:
    s = FakeSerial(device=FakeTurretDevice(eeprom_pan=5, eeprom_tilt=160), timeout=0.05)
    assert lines(s) == [WARNING_LINE, "Turret Ready"]
    assert cmd(s, "GET") == ["OK:5,160"]
