from typing import Callable, Iterator

import pytest

from antenna_tracker.hardware.fake_turret import FAKE_PORT, FakeSerial, FakeTurretDevice
from antenna_tracker.hardware.port_finder import PortIdentity
from antenna_tracker.hardware.turret_client import LinkState, TurretClient

Wait = Callable[..., bool]


class Recorder:
    def __init__(self, client: TurretClient) -> None:
        self.events: list[tuple] = []
        for name in ("connected", "connection_failed", "position", "limit_rejected",
                     "power_lost", "power_restored"):
            getattr(client, name).connect(lambda *a, n=name: self.events.append((n, *a)))

    def names(self) -> list[str]:
        return [e[0] for e in self.events]

    def count(self, name: str) -> int:
        return self.names().count(name)


@pytest.fixture
def dev() -> FakeTurretDevice:
    return FakeTurretDevice(eeprom_pan=100, eeprom_tilt=110)


@pytest.fixture
def client(qapp: object, dev: FakeTurretDevice) -> Iterator[TurretClient]:
    c = TurretClient(
        opener=lambda d: FakeSerial(d, device=dev, timeout=0.02),
        finder=lambda ident: ident.device if dev.powered else None,
        heartbeat_s=0.1, reply_timeout_s=0.15, reconnect_s=0.05, ready_timeout_s=0.1,
    )
    yield c
    c.close()


def start(client: TurretClient, wait_until: Wait) -> Recorder:
    rec = Recorder(client)
    client.open(PortIdentity(FAKE_PORT))
    assert wait_until(lambda: client.is_connected)
    return rec


def test_connect_reads_restored_position(client: TurretClient, wait_until: Wait) -> None:
    rec = start(client, wait_until)
    assert wait_until(lambda: ("position", 100, 110) in rec.events)
    assert client.last_position == (100, 110)


def test_move_and_limit(client: TurretClient, wait_until: Wait, dev: FakeTurretDevice) -> None:
    rec = start(client, wait_until)
    client.move(120, 100)
    assert wait_until(lambda: client.last_position == (120, 100))
    client.move(30, 150)
    assert wait_until(lambda: ("limit_rejected", 30, 150) in rec.events)
    assert dev.current_pan == 120
    client.init()
    assert wait_until(lambda: client.last_position == (90, 90))


def test_heartbeat_keeps_position_fresh(client: TurretClient, wait_until: Wait, dev: FakeTurretDevice) -> None:
    rec = start(client, wait_until)
    dev.current_pan, dev.current_tilt = 95, 95
    assert wait_until(lambda: ("position", 95, 95) in rec.events)


def test_power_loss_and_restore(client: TurretClient, wait_until: Wait, dev: FakeTurretDevice) -> None:
    rec = start(client, wait_until)
    client.move(130, 100)
    assert wait_until(lambda: client.last_position == (130, 100))
    dev.power_off()
    assert wait_until(lambda: rec.count("power_lost") == 1)
    assert client.state is LinkState.POWER_LOST
    client.move(90, 90)
    dev.power_on()
    assert wait_until(lambda: rec.count("power_restored") == 1)
    assert client.is_connected
    assert client.last_position == (130, 100)
    assert dev.current_pan == 130


def test_unresponsive_detected_after_two_missed_heartbeats(
    client: TurretClient, wait_until: Wait, dev: FakeTurretDevice
) -> None:
    rec = start(client, wait_until)
    dev.responsive = False
    assert wait_until(lambda: rec.count("power_lost") == 1)
    assert ("power_lost", "Tracker stopped answering") in rec.events
    dev.responsive = True
    assert wait_until(lambda: rec.count("power_restored") == 1)


def test_unexpected_reboot_detected(client: TurretClient, wait_until: Wait, dev: FakeTurretDevice) -> None:
    rec = start(client, wait_until)
    dev.reboot()
    assert wait_until(lambda: ("power_lost", "Tracker rebooted") in rec.events)
    assert wait_until(lambda: rec.count("power_restored") == 1)


def test_connection_failed_when_absent(qapp: object, wait_until: Wait) -> None:
    c = TurretClient(finder=lambda ident: None, reconnect_s=0.05)
    rec = Recorder(c)
    c.open(PortIdentity("/dev/does-not-exist"))
    try:
        assert wait_until(lambda: rec.count("connection_failed") >= 1)
        assert not c.is_connected
    finally:
        c.close()


def test_warning_lines_ignored(qapp: object, wait_until: Wait) -> None:
    dev = FakeTurretDevice(eeprom_pan=5, eeprom_tilt=160)
    c = TurretClient(
        opener=lambda d: FakeSerial(d, device=dev, timeout=0.02),
        finder=lambda ident: ident.device,
        heartbeat_s=0.1, reply_timeout_s=0.15, ready_timeout_s=0.1,
    )
    try:
        c.open(PortIdentity(FAKE_PORT))
        assert wait_until(lambda: c.last_position == (5, 160))
    finally:
        c.close()
