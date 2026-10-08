import pytest

from antenna_tracker.geo import pointing as pt
from antenna_tracker.geo.pointing import PointingStatus
from antenna_tracker.hardware.fake_turret import FakeTurretDevice

LAT, LON = 31.77, 35.21


def test_wrap180() -> None:
    assert pt.wrap180(190) == -170
    assert pt.wrap180(-190) == 170
    assert pt.wrap180(0) == 0


def test_az_el_north_and_up() -> None:
    lat2, lon2 = pt.destination(LAT, LON, 0, 1000)
    az, el, dist = pt.az_el_dist(LAT, LON, 500, lat2, lon2, 1500)
    assert az == pytest.approx(0, abs=1e-6) or az == pytest.approx(360, abs=1e-6)
    assert dist == pytest.approx(1000, rel=1e-6)
    assert el == pytest.approx(45, abs=1e-6)


def test_pan_mapping_clockwise() -> None:
    assert pt.az_el_to_pan_tilt(100, 10, 90) == (100, 100)
    assert pt.az_el_to_pan_tilt(350, -5, 10) == (70, 85)
    assert pt.pan_tilt_to_az_el(100, 100, 90) == (100, 10)


@pytest.mark.parametrize("pan,lo,hi", [(90, 60, 160), (70, 60, 160), (110, 60, 160),
                                       (30, 60, 120), (150, 60, 120), (5, 85, 95), (175, 85, 95)])
def test_linked_limits(pan: int, lo: float, hi: float) -> None:
    assert pt.tilt_min(pan) == lo and pt.tilt_max(pan) == hi


def test_is_reachable_matches_firmware_exhaustively() -> None:
    dev = FakeTurretDevice()
    for pan in range(-5, 186):
        for tilt in range(50, 171):
            reply = dev.handle_line(f"MOVE,{pan},{tilt}")[0]
            assert pt.is_reachable(pan, tilt) == reply.startswith("OK:"), (pan, tilt)
            if pt.PAN_MIN <= pan <= pt.PAN_MAX:
                in_band = pt.tilt_min(pan) <= tilt <= pt.tilt_max(pan)
                assert in_band == pt.is_reachable(pan, tilt)


def test_clamp_in_range() -> None:
    assert pt.clamp_pan_tilt(100.4, 120.6) == (100, 121, PointingStatus.IN_RANGE)


def test_clamp_azimuth_priority() -> None:
    pan, tilt, status = pt.clamp_pan_tilt(200, 150)
    assert (pan, tilt) == (175, 95) and status is PointingStatus.AZIMUTH_OUT_OF_COVERAGE


def test_clamp_elevation_limited() -> None:
    pan, tilt, status = pt.clamp_pan_tilt(30, 150)
    assert (pan, tilt) == (30, 120) and status is PointingStatus.ELEVATION_LIMITED
    assert pt.clamp_pan_tilt(90, 10)[:2] == (90, 60)


def test_clamped_results_always_reachable() -> None:
    for pan in range(-200, 400, 7):
        for tilt in range(-50, 250, 7):
            p, t, _ = pt.clamp_pan_tilt(pan, tilt)
            assert pt.is_reachable(p, t)


def test_solve_end_to_end() -> None:
    lat2, lon2 = pt.destination(LAT, LON, 120, 2000)
    sol = pt.solve(LAT, LON, 800, lat2, lon2, 800 + 2000 * 0.17632698, ref_az_true=100)
    assert sol.azimuth == pytest.approx(120, abs=0.01)
    assert sol.elevation == pytest.approx(10, abs=0.01)
    assert (sol.pan, sol.tilt, sol.status) == (110, 100, PointingStatus.IN_RANGE)


def test_solve_behind_is_out_of_coverage() -> None:
    lat2, lon2 = pt.destination(LAT, LON, 270, 2000)
    sol = pt.solve(LAT, LON, 0, lat2, lon2, 0, ref_az_true=90)
    assert sol.status is PointingStatus.AZIMUTH_OUT_OF_COVERAGE
    assert sol.pan in (5, 175)


def test_envelope() -> None:
    env = pt.reachable_envelope(5)
    assert env[0] == (5, -5, 5) and env[-1] == (175, -5, 5)
    assert (90, -30, 70) in env
