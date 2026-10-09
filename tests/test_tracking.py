import math
import time

import pytest

from antenna_tracker.geo.pointing import destination
from antenna_tracker.sources.base import DronePosition, PositionSource
from antenna_tracker.sources.simulated import SimulatedSource
from antenna_tracker.tracking.controller import AntennaSite, Mode, TrackingController, TrackStatus

SITE = AntennaSite(31.77, 35.21, 800.0, ref_az_true=90.0)


class FakeTurret:
    def __init__(self) -> None:
        self.is_connected = True
        self.last_position: tuple[int, int] | None = (90, 90)
        self.moves: list[tuple[int, int]] = []

    def move(self, pan: int, tilt: int) -> None:
        self.moves.append((pan, tilt))
        self.last_position = (pan, tilt)


@pytest.fixture
def setup(qapp: object) -> tuple[TrackingController, FakeTurret, PositionSource]:
    turret = FakeTurret()
    src = PositionSource()
    return TrackingController(turret, SITE, src, stale_timeout_s=5), turret, src


def put(src: PositionSource, az: float, dist: float, alt: float, t: float | None = None) -> None:
    lat, lon = destination(SITE.lat, SITE.lon, az, dist)
    src.publish(DronePosition(lat, lon, alt, time.time() if t is None else t))


def test_auto_moves_with_deadband(setup) -> None:
    ctl, turret, src = setup
    put(src, 100, 3000, 800)
    ctl.tick()
    assert turret.moves == [(100, 90)]
    put(src, 100.3, 3000, 800)
    ctl.tick()
    assert turret.moves == [(100, 90)]
    put(src, 101.2, 3000, 800)
    ctl.tick()
    assert turret.moves[-1] == (101, 90)
    assert ctl.status is TrackStatus.TRACKING


def test_stale_holds(setup) -> None:
    ctl, turret, src = setup
    put(src, 120, 3000, 800, t=time.time() - 10)
    ctl.tick()
    assert turret.moves == [] and ctl.status is TrackStatus.STALE


def test_no_position(setup) -> None:
    ctl, turret, _ = setup
    ctl.tick()
    assert ctl.status is TrackStatus.NO_POSITION


def test_manual_stops_auto_but_recommends(setup) -> None:
    ctl, turret, src = setup
    got = []
    ctl.recommendation.connect(got.append)
    ctl.set_mode(Mode.MANUAL)
    put(src, 120, 3000, 800)
    ctl.tick()
    assert turret.moves == [] and ctl.status is TrackStatus.MANUAL
    assert got[-1] is not None and got[-1].pan == 120
    assert ctl.point_to_recommended() and turret.moves == [(120, 90)]


def test_nudge_respects_limits(setup) -> None:
    ctl, turret, _ = setup
    turret.last_position = (30, 120)
    assert ctl.manual_target(0, 1) is None
    assert not ctl.nudge(0, 1)
    assert ctl.nudge(0, -5) and turret.moves == [(30, 115)]
    assert ctl.mode is Mode.MANUAL


def test_out_of_range_and_no_power(setup) -> None:
    ctl, turret, src = setup
    put(src, 300, 3000, 800)
    ctl.tick()
    assert ctl.status is TrackStatus.OUT_OF_RANGE
    turret.is_connected = False
    ctl.tick()
    assert ctl.status is TrackStatus.NO_POWER


def test_simulated_source_rejects_5km_jump(qapp: object) -> None:
    sim = SimulatedSource()
    jams: list[bool] = []
    sim.possible_jamming.connect(lambda: jams.append(True))
    sim.set_position(31.77, 35.21, 800)
    near = 31.77 + math.degrees(1000 / 6_371_000)
    sim.set_position(near, 35.21)
    assert jams == [] and sim.latest().lat == pytest.approx(near)
    kept = sim.latest()
    sim.set_position(near + math.degrees(6000 / 6_371_000), 35.21)
    assert jams == [True]
    assert sim.latest() is kept


def test_simulated_source_circle(qapp: object) -> None:
    sim = SimulatedSource()
    sim.set_position(31.0, 35.0, 500)
    assert sim.latest().alt_amsl == 500
    sim.start_circle(SITE.lat, SITE.lon, 1000, period_s=40)
    sim.stop_circle()
    p0 = sim.latest()
    sim.step_circle(10)
    p1 = sim.latest()
    assert (p0.lat, p0.lon) != (p1.lat, p1.lon)
    ctl = TrackingController(FakeTurret(), SITE, sim)
    sol = ctl.compute()
    assert sol is not None and sol.azimuth == pytest.approx(90, abs=0.1)
    assert sol.distance_m == pytest.approx(1000, rel=1e-3)
