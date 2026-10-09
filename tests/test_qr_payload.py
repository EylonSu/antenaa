import pytest

from antenna_tracker.config import AppConfig, QrFields, load_config, save_config
from antenna_tracker.sources.qr_payload import QrParseError, parse_payload

SAMPLE_1 = "1748FEV3HMK824291553|0.0|0.0|-7.8525233|-60.916748|-52.309998|198.534|0.0|11.69|1|0.5083778|4|3437.2869|-22918.311805|73.8062|58.66283|[]"
SAMPLE_2 = "1748FEV3HMK824291553|0.0|0.0|-4.920544|-64.030846|-43.479996|198.587|0.0|18.39|1|1.1626538|4|3446.241|-22918.311805|73.8062|58.66283|[]"


def with_coords(sample: str, lat: str, lon: str) -> str:
    parts = sample.split("|")
    parts[1], parts[2] = lat, lon
    return "|".join(parts)


@pytest.mark.parametrize("text,rel_alt,home", [(SAMPLE_1, 198.534, 3437.2869), (SAMPLE_2, 198.587, 3446.241)])
def test_real_samples_have_no_gps(text: str, rel_alt: float, home: float) -> None:
    t = parse_payload(text, QrFields())
    assert t.serial == "1748FEV3HMK824291553"
    assert not t.has_gps
    assert t.rel_alt == pytest.approx(rel_alt)
    assert t.home_dist == pytest.approx(home)
    assert t.reported_antenna_dist == pytest.approx(-22918.311805)
    assert t.raw == text


def test_heading_normalized() -> None:
    assert parse_payload(SAMPLE_1).heading == pytest.approx(360 - 52.309998)


def test_valid_coordinates() -> None:
    t = parse_payload(with_coords(SAMPLE_1, "31.7712", " 35.2134 "))
    assert t.has_gps
    assert (t.lat, t.lon) == (pytest.approx(31.7712), pytest.approx(35.2134))


def test_only_one_zero_is_still_gps() -> None:
    assert parse_payload(with_coords(SAMPLE_1, "0.0", "35.2")).has_gps


def test_too_few_fields() -> None:
    with pytest.raises(QrParseError, match="too few fields"):
        parse_payload("abc|31.7|35.2")


@pytest.mark.parametrize("idx", [1, 2, 6])
def test_non_numeric_field(idx: int) -> None:
    parts = SAMPLE_1.split("|")
    parts[idx] = "x"
    with pytest.raises(QrParseError, match=f"field {idx} is not a number"):
        parse_payload("|".join(parts))


def test_nan_rejected() -> None:
    with pytest.raises(QrParseError):
        parse_payload(with_coords(SAMPLE_1, "nan", "35.2"))


@pytest.mark.parametrize("lat,lon", [("91", "35"), ("31", "-181")])
def test_coordinates_out_of_range(lat: str, lon: str) -> None:
    with pytest.raises(QrParseError, match="out of range"):
        parse_payload(with_coords(SAMPLE_1, lat, lon))


def test_bad_optional_field_is_none() -> None:
    parts = SAMPLE_1.split("|")
    parts[12] = "?"
    assert parse_payload("|".join(parts)).home_dist is None


def test_custom_field_indices() -> None:
    f = QrFields(serial=3, lat=0, lon=1, rel_alt=2, heading=None, home_dist=None, antenna_dist=None)
    t = parse_payload("31.5|35.1|120|SN9", f)
    assert (t.serial, t.lat, t.lon, t.rel_alt) == ("SN9", 31.5, 35.1, 120.0)
    assert t.heading is None and t.home_dist is None and t.reported_antenna_dist is None


def test_config_round_trip(tmp_path) -> None:
    p = tmp_path / "c.json"
    cfg = AppConfig(takeoff_near_antenna=False, takeoff_alt_amsl=412.0, qr_fields=QrFields(lat=7),
                    map_basemap="satellite")
    save_config(cfg, p)
    back = load_config(p)
    assert back.qr_fields == QrFields(lat=7)
    assert back.takeoff_alt_amsl == 412.0 and not back.takeoff_near_antenna
    assert back.qr_bounds == cfg.qr_bounds
    assert back.effective_takeoff_alt_amsl == 412.0
    assert back.map_basemap == "satellite"
    assert AppConfig(antenna_alt_amsl=800).effective_takeoff_alt_amsl == 800
    p.write_text(p.read_text(encoding="utf-8").replace('"satellite"', '"roadmap"'), encoding="utf-8")
    assert load_config(p).map_basemap == "osm"
