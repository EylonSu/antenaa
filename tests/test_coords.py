import pytest

from antenna_tracker.geo import coords
from antenna_tracker.geo.coords import UtmError


def test_parse_halves_prefixes_northing_with_3() -> None:
    assert coords.parse_utm("684000", "516000") == (684000.0, 3516000.0)


def test_parse_12_digits_with_spaces() -> None:
    assert coords.parse_utm12("684000 516000") == (684000.0, 3516000.0)


@pytest.mark.parametrize("e,n,msg", [
    ("", "516000", "easting"),
    ("68400", "516000", "exactly 6"),
    ("68400a", "516000", "digits only"),
    ("684000", "5160000", "exactly 6"),
])
def test_invalid_inputs(e: str, n: str, msg: str) -> None:
    with pytest.raises(UtmError, match=msg):
        coords.parse_utm(e, n)


def test_bad_12_digit_string() -> None:
    with pytest.raises(UtmError):
        coords.parse_utm12("12345")


def test_jerusalem_roundtrip() -> None:
    p = coords.utm_input_to_latlon("711000", "513000")
    assert 31.6 < p.lat < 31.9 and 35.1 < p.lon < 35.3
    e, n = coords.latlon_to_utm(p.lat, p.lon)
    assert abs(e - 711000) < 0.01 and abs(n - 3513000) < 0.01


def test_outside_israel_rejected() -> None:
    with pytest.raises(UtmError, match="outside Israel"):
        coords.utm_input_to_latlon("200000", "513000")
