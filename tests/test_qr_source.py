import math
import time

import pytest

from antenna_tracker.config import AppConfig
from antenna_tracker.geo.pointing import destination
from antenna_tracker.sources.qr_video import QrVideoSource
from antenna_tracker.tracking.controller import AntennaSite, Mode, TrackingController, TrackStatus

from test_qr_payload import SAMPLE_1, SAMPLE_2, with_coords

SITE = AntennaSite(31.77, 35.21, 800.0, ref_az_true=90.0)


def fix(lat: float, lon: float, sample: str = SAMPLE_1) -> str:
    return with_coords(sample, f"{lat:.7f}", f"{lon:.7f}")


def at(dist: float, az: float = 90.0) -> str:
    return fix(*destination(SITE.lat, SITE.lon, az, dist))


@pytest.fixture
def src(qapp) -> QrVideoSource:
    return QrVideoSource(takeoff_alt_amsl=800.0)


class Rec:
    def __init__(self, src: QrVideoSource) -> None:
        self.events: list[str] = []
        self.positions = []
        self.telemetry = []
        src.gps_lost.connect(lambda: self.events.append("lost"))
        src.gps_restored.connect(lambda: self.events.append("restored"))
        src.position_changed.connect(self.positions.append)
        src.telemetry.connect(self.telemetry.append)


def test_altitude_relative_to_takeoff(src) -> None:
    r = Rec(src)
    src.feed(at(1000), 100.0)
    p = src.latest()
    assert p.alt_amsl == pytest.approx(800 + 198.534)
    assert p.t == 100.0
    assert len(r.positions) == 1 and len(r.telemetry) == 1


def test_from_config_uses_antenna_alt_when_near(qapp) -> None:
    assert QrVideoSource.from_config(AppConfig(antenna_alt_amsl=650)).takeoff_alt_amsl == 650
    cfg = AppConfig(antenna_alt_amsl=650, takeoff_near_antenna=False, takeoff_alt_amsl=300)
    assert QrVideoSource.from_config(cfg).takeoff_alt_amsl == 300


def test_rejects_outside_israel(src) -> None:
    r = Rec(src)
    src.feed(fix(48.85, 2.35), 1.0)
    assert src.latest() is None and r.positions == []
    assert src.rejected_count == 1 and src.rejected_by_reason == {"outside area": 1}
    assert len(r.telemetry) == 1


def test_rejects_jumps(src) -> None:
    src.feed(at(1000), 0.0)
    src.feed(at(1050), 1.0)       # 50 m/s ok
    src.feed(at(1200), 2.0)       # 150 m/s rejected
    assert src.rejected_by_reason == {"too fast": 1}
    src.feed(at(1150), 3.0)       # 50 m/s from last accepted (t=1)... over 2 s
    assert src.latest().t == 3.0


def _km_north(src: QrVideoSource, meters: float) -> str:
    prev = src.latest()
    lat = prev.lat + math.degrees(meters / 6_371_000.0)
    return fix(lat, prev.lon)


def test_possible_jamming_on_5km_jump(src) -> None:
    jams: list[bool] = []
    src.possible_jamming.connect(lambda: jams.append(True))

    def jump(dt: float) -> None:
        src.reset()
        jams.clear()
        src.feed(at(1000), 0.0)
        src.feed(_km_north(src, 5100), dt)

    for dt in (1.0, 0.2, 0.0):
        jump(dt)
        assert jams == [True]
        assert src.rejected_by_reason == {"possible jamming": 1}
        assert src.latest().t == 0.0

    jump(2.0)
    assert jams == []
    assert src.rejected_by_reason == {"too fast": 1}
    assert src.latest().t == 0.0


def test_controller_possible_jamming_switches_to_manual(src) -> None:
    ctl = TrackingController(FakeTurret(), SITE, src)
    src.possible_jamming.connect(lambda: ctl.set_mode(Mode.MANUAL))
    t = time.time()
    src.feed(at(1000), t)
    ctl.tick()
    assert ctl.mode is Mode.AUTO and ctl.status is TrackStatus.TRACKING
    src.feed(_km_north(src, 5100), t + 0.2)
    assert ctl.mode is Mode.MANUAL and ctl.status is TrackStatus.MANUAL
    assert src.latest().t == t


def test_parse_error_counted(src) -> None:
    errs = []
    src.parse_failed.connect(errs.append)
    src.feed("garbage", 1.0)
    assert src.parse_errors == 1 and errs and src.last_raw == "garbage"


def test_gps_lost_and_restored_debounced(src) -> None:
    r = Rec(src)
    src.feed(at(1000), 0.0)
    src.feed(SAMPLE_1, 1.0)
    src.feed(SAMPLE_2, 2.0)
    src.feed(at(1000), 3.0)       # breaks the run
    src.feed(SAMPLE_1, 4.0)
    src.feed(SAMPLE_2, 5.0)
    assert r.events == []
    src.feed(SAMPLE_1, 6.0)
    assert r.events == ["lost"] and not src.gps_ok
    src.feed(SAMPLE_1, 7.0)
    assert r.events == ["lost"]
    src.feed(at(1000), 8.0)
    src.feed(at(1010), 9.0)
    src.feed(SAMPLE_1, 10.0)      # breaks the good run
    src.feed(at(1010), 11.0)
    src.feed(at(1010), 12.0)
    assert r.events == ["lost"]
    src.feed(at(1010), 13.0)
    assert r.events == ["lost", "restored"] and src.gps_ok


def test_no_gps_readings_not_published(src) -> None:
    r = Rec(src)
    for i in range(5):
        src.feed(SAMPLE_1, float(i))
    assert r.positions == [] and len(r.telemetry) == 5


class FakeTurret:
    is_connected = True
    last_position = (90, 90)

    def __init__(self) -> None:
        self.moves = []

    def move(self, pan: int, tilt: int) -> None:
        self.moves.append((pan, tilt))


def test_controller_no_gps_flow(src) -> None:
    ctl = TrackingController(FakeTurret(), SITE, src)
    src.gps_lost.connect(ctl.on_gps_lost)
    src.gps_restored.connect(ctl.on_gps_restored)
    statuses = []
    ctl.status_changed.connect(statuses.append)
    src.feed(at(1000))
    ctl.tick()
    assert ctl.status is TrackStatus.TRACKING
    for _ in range(3):
        src.feed(SAMPLE_1)
    assert ctl.mode is Mode.MANUAL and ctl.status is TrackStatus.NO_GPS
    assert not ctl.drone_gps_ok
    for _ in range(3):
        src.feed(at(1000))
    assert ctl.drone_gps_ok
    assert ctl.mode is Mode.MANUAL and ctl.status is TrackStatus.MANUAL
    ctl.set_mode(Mode.AUTO)
    assert ctl.status is TrackStatus.TRACKING
    assert "no_gps" in statuses


def test_controller_no_power_beats_no_gps(qapp) -> None:
    t = FakeTurret()
    t.is_connected = False
    ctl = TrackingController(t, SITE, None)
    ctl.set_drone_gps(False)
    assert ctl.status is TrackStatus.NO_POWER
