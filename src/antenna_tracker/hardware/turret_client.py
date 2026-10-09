from __future__ import annotations

import queue
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

import serial
from PySide6.QtCore import QObject, QThread, Signal

from antenna_tracker.hardware import port_finder
from antenna_tracker.hardware.port_finder import PortIdentity, SerialLike
from antenna_tracker.i18n import ltr, t


class LinkState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    POWER_LOST = "power_lost"


@dataclass(frozen=True)
class _Cmd:
    text: str
    pan: int | None = None
    tilt: int | None = None


class _Stop(Exception):
    pass


class _Lost(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class _Worker(QThread):
    connected = Signal(str)
    connection_failed = Signal(str)
    position = Signal(int, int)
    limit_rejected = Signal(int, int)
    power_lost = Signal(str)
    power_restored = Signal()
    state_changed = Signal(str)
    line_received = Signal(str)

    def __init__(
        self,
        identity: PortIdentity,
        opener: Callable[[str], SerialLike],
        finder: Callable[[PortIdentity], str | None],
        heartbeat_s: float,
        reply_timeout_s: float,
        reconnect_s: float,
        ready_timeout_s: float,
    ) -> None:
        super().__init__()
        self.identity = identity
        self._opener = opener
        self._finder = finder
        self.heartbeat_s = heartbeat_s
        self.reply_timeout_s = reply_timeout_s
        self.reconnect_s = reconnect_s
        self.ready_timeout_s = ready_timeout_s
        self.commands: queue.Queue[_Cmd | None] = queue.Queue()
        self._stopping = False
        self._ser: SerialLike | None = None
        self._state = LinkState.DISCONNECTED
        self._ever_connected = False
        self._missed = 0
        self.simulated_power = True

    def stop(self) -> None:
        self._stopping = True
        self.commands.put(None)

    def _set_state(self, state: LinkState) -> None:
        if state is not self._state:
            self._state = state
            self.state_changed.emit(state.value)

    def run(self) -> None:
        try:
            while not self._stopping:
                if self._ser is None:
                    self._try_connect()
                    continue
                try:
                    self._service_once()
                except _Lost as e:
                    self._on_lost(e.reason)
        except _Stop:
            pass
        finally:
            self._close()
            self._set_state(LinkState.DISCONNECTED)

    def _sleep(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while not self._stopping and time.monotonic() < deadline:
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        if self._stopping:
            raise _Stop

    def _close(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            except (serial.SerialException, OSError):
                pass
            self._ser = None

    def _wait_for_simulated_power(self) -> None:
        while not self._stopping and not self.simulated_power:
            time.sleep(0.05)
        if self._stopping:
            raise _Stop

    def _try_connect(self) -> None:
        if not self.simulated_power:
            self._wait_for_simulated_power()
            return
        if self._state is not LinkState.POWER_LOST:
            self._set_state(LinkState.CONNECTING)
        device = self._finder(self.identity)
        if device is None:
            if not self._ever_connected:
                self.connection_failed.emit(
                    t("Port {device} not found").format(device=ltr(self.identity.device)))
            self._sleep(self.reconnect_s)
            return
        try:
            ser = self._opener(device)
        except (serial.SerialException, OSError) as e:
            if not self._ever_connected:
                self.connection_failed.emit(str(e))
            self._sleep(self.reconnect_s)
            return
        try:
            pan, tilt = port_finder.handshake(ser, self.ready_timeout_s, self.reply_timeout_s)
        except (TimeoutError, serial.SerialException, OSError) as e:
            try:
                ser.close()
            except (serial.SerialException, OSError):
                pass
            if not self._ever_connected:
                self.connection_failed.emit(t("No tracker answered: {err}").format(err=ltr(e)))
            self._sleep(self.reconnect_s)
            return
        self._ser = ser
        self._missed = 0
        self._drain_commands()
        was_lost = self._state is LinkState.POWER_LOST
        self._ever_connected = True
        self._set_state(LinkState.CONNECTED)
        self.connected.emit(device)
        self.position.emit(pan, tilt)
        if was_lost:
            self.power_restored.emit()

    def _drain_commands(self) -> None:
        while True:
            try:
                if self.commands.get_nowait() is None:
                    raise _Stop
            except queue.Empty:
                return

    def _next_command(self) -> _Cmd | None:
        try:
            cmd = self.commands.get(timeout=self.heartbeat_s)
        except queue.Empty:
            return None
        if cmd is None:
            raise _Stop
        if cmd.pan is not None:
            while True:
                try:
                    nxt = self.commands.get_nowait()
                except queue.Empty:
                    break
                if nxt is None:
                    raise _Stop
                if nxt.pan is None:
                    self.commands.put(nxt)
                    break
                cmd = nxt
        return cmd

    def _service_once(self) -> None:
        cmd = self._next_command()
        if not self.simulated_power:
            raise _Lost(t("Simulated power off"))
        heartbeat = cmd is None
        if heartbeat and self._finder(self.identity) is None:
            raise _Lost(t("Tracker port disappeared"))
        reply = self._transact(cmd.text if cmd else "GET")
        if reply is None:
            if heartbeat:
                self._missed += 1
                if self._missed >= 2:
                    raise _Lost(t("Tracker stopped answering"))
            return
        self._missed = 0
        if reply == "LIMIT" or reply == "LINIT":
            if cmd is not None and cmd.pan is not None and cmd.tilt is not None:
                self.limit_rejected.emit(cmd.pan, cmd.tilt)
            return
        pos = port_finder.parse_ok(reply)
        if pos is not None:
            self.position.emit(*pos)

    def _transact(self, text: str) -> str | None:
        assert self._ser is not None
        try:
            self._ser.write((text + "\n").encode("utf-8"))
            self._ser.flush()
            deadline = time.monotonic() + self.reply_timeout_s
            while time.monotonic() < deadline:
                if self._stopping:
                    raise _Stop
                if not self.simulated_power:
                    raise _Lost(t("Simulated power off"))
                line = port_finder.read_line(self._ser)
                if not line:
                    continue
                self.line_received.emit(line)
                if line == "Turret Ready":
                    raise _Lost(t("Tracker rebooted"))
                if line.startswith("OK:") or line in ("LIMIT", "LINIT"):
                    return line
            return None
        except (serial.SerialException, OSError) as e:
            raise _Lost(t("Serial error: {err}").format(err=ltr(e))) from e

    def _on_lost(self, reason: str) -> None:
        self._close()
        self._drain_commands()
        self._set_state(LinkState.POWER_LOST)
        self.power_lost.emit(reason)


class TurretClient(QObject):
    """Owns the serial worker thread; all signals are delivered on the owner's thread."""

    connected = Signal(str)
    connection_failed = Signal(str)
    position = Signal(int, int)
    limit_rejected = Signal(int, int)
    power_lost = Signal(str)
    power_restored = Signal()
    state_changed = Signal(str)
    line_received = Signal(str)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        opener: Callable[[str], SerialLike] = port_finder.open_serial,
        finder: Callable[[PortIdentity], str | None] = port_finder.find_port,
        heartbeat_s: float = 1.0,
        reply_timeout_s: float = 2.0,
        reconnect_s: float = 1.0,
        ready_timeout_s: float = 3.0,
    ) -> None:
        super().__init__(parent)
        self._opener = opener
        self._finder = finder
        self._timing = (heartbeat_s, reply_timeout_s, reconnect_s, ready_timeout_s)
        self._worker: _Worker | None = None
        self._state = LinkState.DISCONNECTED
        self._pan: int | None = None
        self._tilt: int | None = None
        self.state_changed.connect(self._on_state)
        self.position.connect(self._on_position)

    @property
    def state(self) -> LinkState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state is LinkState.CONNECTED

    @property
    def last_position(self) -> tuple[int, int] | None:
        return None if self._pan is None or self._tilt is None else (self._pan, self._tilt)

    def _on_state(self, value: str) -> None:
        self._state = LinkState(value)

    def _on_position(self, pan: int, tilt: int) -> None:
        self._pan, self._tilt = pan, tilt

    def open(self, identity: PortIdentity) -> None:
        self.close()
        w = _Worker(identity, self._opener, self._finder, *self._timing)
        for name in ("connected", "connection_failed", "position", "limit_rejected",
                     "power_lost", "power_restored", "state_changed", "line_received"):
            getattr(w, name).connect(getattr(self, name))
        self._worker = w
        w.start()

    def close(self, wait_ms: int = 5000) -> None:
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait(wait_ms)
            self._worker = None
        self._state = LinkState.DISCONNECTED

    def set_simulated_power(self, on: bool) -> None:
        """Drop or restore the live link without unplugging the tracker."""
        if self._worker is None:
            return
        self._worker.simulated_power = on
        if not on:
            self._worker.commands.put(_Cmd("GET"))

    def _send(self, cmd: _Cmd) -> None:
        if self._worker is not None:
            self._worker.commands.put(cmd)

    def init(self) -> None:
        self._send(_Cmd("INIT"))

    def get(self) -> None:
        self._send(_Cmd("GET"))

    def move(self, pan: int, tilt: int) -> None:
        self._send(_Cmd(f"MOVE,{int(pan)},{int(tilt)}", int(pan), int(tilt)))
