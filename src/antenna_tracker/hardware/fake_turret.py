"""Simulated DiffTurret firmware usable as a drop-in for serial.Serial."""
from __future__ import annotations

import re
import threading
import time
from collections import deque

import serial

FAKE_PORT = "fake://turret"
FAKE_VID = 0xFFFF
FAKE_PID = 0x0001
FAKE_SERIAL_NUMBER = "FAKE0001"

PAN_MIN, PAN_MAX = 5, 175
TILT_MIN, TILT_MAX = 60, 160
WARNING_LINE = "\u26a0\ufe0f WARNING: Coordinate outside physical limits. Clamped."

_INT_RE = re.compile(r"^\s*([+-]?\d+)")


def arduino_to_int(text: str) -> int:
    m = _INT_RE.match(text)
    return int(m.group(1)) if m else 0


class FakeTurretDevice:
    """The physical board: EEPROM, power state and firmware logic."""

    def __init__(self, eeprom_pan: int = 90, eeprom_tilt: int = 90) -> None:
        self._lock = threading.RLock()
        self.eeprom = [eeprom_pan & 0xFF, eeprom_tilt & 0xFF]
        self.powered = True
        self.responsive = True
        self.current_pan = 90
        self.current_tilt = 90
        self.move_count = 0
        self._ports: list[FakeSerial] = []

    def boot(self) -> list[str]:
        with self._lock:
            pan, tilt = self.eeprom
            if pan < PAN_MIN or pan > PAN_MAX or tilt < TILT_MIN or tilt > TILT_MAX:
                pan, tilt = 90, 90
            self.current_pan, self.current_tilt = pan, tilt
            out: list[str] = []
            if not self._differential_ok(pan, tilt):
                out.append(WARNING_LINE)
            out.append("Turret Ready")
            return out

    @staticmethod
    def _differential_ok(pan: int, tilt: int) -> bool:
        raw_left = (180 - pan) + (180 - tilt) - 90
        raw_right = (180 - pan) - (180 - tilt) + 90
        return 0 <= raw_left <= 180 and 0 <= raw_right <= 180

    def _ok(self) -> str:
        return f"OK:{self.current_pan},{self.current_tilt}"

    def _move_to(self, pan: int, tilt: int) -> list[str]:
        if pan < PAN_MIN or pan > PAN_MAX or tilt < TILT_MIN or tilt > TILT_MAX:
            return ["LIMIT"]
        if not self._differential_ok(pan, tilt):
            return ["LIMIT"]
        self.current_pan, self.current_tilt = pan, tilt
        self.eeprom = [pan & 0xFF, tilt & 0xFF]
        self.move_count += 1
        return [self._ok()]

    def handle_line(self, raw: str) -> list[str]:
        with self._lock:
            line = raw.strip()
            if line.upper() == "INIT":
                return self._move_to(90, 90)
            if line.upper() == "GET":
                return [self._ok()]
            if line.startswith("MOVE,"):
                first = line.index(",")
                second = line.find(",", first + 1)
                if second == -1:
                    return []
                pan = arduino_to_int(line[first + 1:second])
                tilt = arduino_to_int(line[second + 1:])
                return self._move_to(pan, tilt)
            return []

    def attach(self, port: FakeSerial) -> None:
        with self._lock:
            if not self.powered:
                raise serial.SerialException(f"could not open port {FAKE_PORT}: device not found")
            self._ports.append(port)
            port._push(self.boot())

    def detach(self, port: FakeSerial) -> None:
        with self._lock:
            if port in self._ports:
                self._ports.remove(port)

    def power_off(self) -> None:
        with self._lock:
            self.powered = False
            for p in self._ports:
                p._kill()
            self._ports.clear()

    def power_on(self) -> None:
        with self._lock:
            self.powered = True

    def reboot(self) -> None:
        """Brief brown-out where the USB device stays enumerated."""
        with self._lock:
            lines = self.boot()
            for p in self._ports:
                p._push(lines)


DEFAULT_DEVICE = FakeTurretDevice()


class FakeSerial:
    """Minimal serial.Serial lookalike talking to a FakeTurretDevice."""

    def __init__(
        self,
        port: str = FAKE_PORT,
        baudrate: int = 9600,
        timeout: float | None = 1.0,
        device: FakeTurretDevice | None = None,
        **_: object,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.device = device or DEFAULT_DEVICE
        self._rx: deque[bytes] = deque()
        self._cond = threading.Condition()
        self._dead = False
        self._open = False
        self._inbuf = b""
        self.open()

    def open(self) -> None:
        self._dead = False
        self._rx.clear()
        self.device.attach(self)
        self._open = True

    @property
    def is_open(self) -> bool:
        return self._open

    @property
    def in_waiting(self) -> int:
        self._check()
        return sum(len(b) for b in self._rx)

    def _push(self, lines: list[str]) -> None:
        with self._cond:
            for line in lines:
                self._rx.append((line + "\r\n").encode("utf-8"))
            self._cond.notify_all()

    def _kill(self) -> None:
        with self._cond:
            self._dead = True
            self._cond.notify_all()

    def _check(self) -> None:
        if self._dead:
            raise serial.SerialException("device reports readiness to read but returned no data")
        if not self._open:
            raise serial.PortNotOpenError()

    def write(self, data: bytes) -> int:
        self._check()
        self._inbuf += data
        while b"\n" in self._inbuf:
            raw, self._inbuf = self._inbuf.split(b"\n", 1)
            if self.device.responsive:
                self._push(self.device.handle_line(raw.decode("utf-8", errors="ignore")))
        return len(data)

    def flush(self) -> None:
        self._check()

    def readline(self) -> bytes:
        deadline = None if self.timeout is None else time.monotonic() + self.timeout
        with self._cond:
            while True:
                self._check()
                if self._rx:
                    return self._rx.popleft()
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    return b""
                self._cond.wait(remaining)

    def reset_input_buffer(self) -> None:
        with self._cond:
            self._rx.clear()

    def reset_output_buffer(self) -> None:
        self._inbuf = b""

    def close(self) -> None:
        if self._open:
            self.device.detach(self)
        self._open = False

    def __enter__(self) -> FakeSerial:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
