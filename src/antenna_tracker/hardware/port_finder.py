from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

import serial
from serial.tools import list_ports

from antenna_tracker.hardware import fake_turret
from antenna_tracker.i18n import ltr, t

BAUD_RATE = 9600

KNOWN_VENDORS: dict[int, str] = {
    0x2341: "Arduino",
    0x2A03: "Arduino",
    0x1A86: "CH340",
    0x0403: "FTDI",
    0x10C4: "CP210x",
}


@dataclass(frozen=True)
class PortIdentity:
    device: str
    vid: int | None = None
    pid: int | None = None
    serial_number: str | None = None


@dataclass(frozen=True)
class PortInfo:
    device: str
    description: str
    vid: int | None
    pid: int | None
    serial_number: str | None
    recommended: bool
    vendor: str | None = None

    @property
    def identity(self) -> PortIdentity:
        return PortIdentity(self.device, self.vid, self.pid, self.serial_number)

    @property
    def label(self) -> str:
        suffix = t("  (Recommended)") if self.recommended else ""
        return f"{ltr(self.device)} - {self.description}{suffix}"


@dataclass(frozen=True)
class TestResult:
    ok: bool
    message: str
    pan: int | None = None
    tilt: int | None = None


class SerialLike(Protocol):
    timeout: float | None

    def write(self, data: bytes) -> int: ...
    def readline(self) -> bytes: ...
    def flush(self) -> None: ...
    def reset_input_buffer(self) -> None: ...
    def close(self) -> None: ...


def is_fake(device: str) -> bool:
    return device.startswith("fake://")


def open_serial(device: str, timeout: float = 0.1) -> SerialLike:
    if is_fake(device):
        return fake_turret.FakeSerial(device, BAUD_RATE, timeout=timeout)
    return serial.Serial(device, BAUD_RATE, timeout=timeout)


def _fake_info() -> PortInfo:
    return PortInfo(
        fake_turret.FAKE_PORT, t("Simulated tracker"), fake_turret.FAKE_VID,
        fake_turret.FAKE_PID, fake_turret.FAKE_SERIAL_NUMBER, False, "Simulator",
    )


def list_candidates(include_fake: bool = False) -> list[PortInfo]:
    """All serial ports, known Arduino/USB-serial vendors first and marked recommended."""
    ports: list[PortInfo] = []
    for p in list_ports.comports():
        vendor = KNOWN_VENDORS.get(p.vid) if p.vid is not None else None
        ports.append(PortInfo(
            p.device, p.description or p.device, p.vid, p.pid, p.serial_number,
            vendor is not None, vendor,
        ))
    ports.sort(key=lambda i: (not i.recommended, i.vid is None, i.device))
    if include_fake and fake_turret.DEFAULT_DEVICE.powered:
        ports.append(_fake_info())
    return ports


def find_port(identity: PortIdentity) -> str | None:
    """Locate the same physical device again; COM numbers may change on Windows."""
    if is_fake(identity.device):
        return identity.device if fake_turret.DEFAULT_DEVICE.powered else None
    ports = list(list_ports.comports())
    if identity.vid is not None and identity.serial_number:
        for p in ports:
            if (p.vid, p.pid, p.serial_number) == (identity.vid, identity.pid, identity.serial_number):
                return p.device
    for p in ports:
        if p.device == identity.device:
            return p.device
    if identity.vid is not None:
        matches = [p for p in ports if (p.vid, p.pid) == (identity.vid, identity.pid)]
        if len(matches) == 1:
            return matches[0].device
    return None


def parse_ok(line: str) -> tuple[int, int] | None:
    if not line.startswith("OK:"):
        return None
    try:
        pan, tilt = line[3:].split(",")
        return int(pan), int(tilt)
    except ValueError:
        return None


def read_line(ser: SerialLike) -> str:
    return ser.readline().decode("utf-8", errors="ignore").strip()


def handshake(ser: SerialLike, ready_timeout: float = 3.0, reply_timeout: float = 2.0) -> tuple[int, int]:
    """Wait for 'Turret Ready' (best effort) then GET; raise on failure."""
    deadline = time.monotonic() + ready_timeout
    while time.monotonic() < deadline:
        if read_line(ser) == "Turret Ready":
            break
    ser.reset_input_buffer()
    ser.write(b"GET\n")
    ser.flush()
    deadline = time.monotonic() + reply_timeout
    while time.monotonic() < deadline:
        pos = parse_ok(read_line(ser))
        if pos is not None:
            return pos
    raise TimeoutError(t("No reply to GET"))


def test_port(device: str, ready_timeout: float = 3.0) -> TestResult:
    try:
        ser = open_serial(device)
    except (serial.SerialException, OSError) as e:
        return TestResult(False, t("Could not open {device}: {err}").format(device=ltr(device), err=ltr(e)))
    try:
        pan, tilt = handshake(ser, ready_timeout)
        return TestResult(
            True,
            t("Tracker found (pan {pan}, tilt {tilt})").format(pan=ltr(pan), tilt=ltr(tilt)),
            pan, tilt,
        )
    except (TimeoutError, serial.SerialException, OSError) as e:
        return TestResult(
            False, t("No tracker answered on {device}: {err}").format(device=ltr(device), err=ltr(e)),
        )
    finally:
        ser.close()
