import pytest

from antenna_tracker.ui.tiles import OSM_TILE_URL, SATELLITE_TILE_URL, parse_tile_path

SATELLITE_PREFIX = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/"


def test_osm_tile_keeps_z_x_y_order():
    url, mime = parse_tile_path("/osm/3/2/1.png")
    assert url == OSM_TILE_URL.format(z=3, x=2, y=1)
    assert url == "https://tile.openstreetmap.org/3/2/1.png"
    assert mime == b"image/png"
    url2, mime2 = parse_tile_path("osm/12/345/678.png")
    assert url2 == "https://tile.openstreetmap.org/12/345/678.png"
    assert mime2 == b"image/png"


def test_satellite_tile_puts_row_before_column():
    url, mime = parse_tile_path("/satellite/8/10/20.jpg")
    assert url == SATELLITE_TILE_URL.format(z=8, y=20, x=10)
    assert url == SATELLITE_PREFIX + "8/20/10.jpg"
    assert mime == b"image/jpeg"
    url2, _ = parse_tile_path("satellite/5/17/11.jpg")
    assert url2 == SATELLITE_PREFIX + "5/11/17.jpg"


@pytest.mark.parametrize("path", [
    "",
    "/",
    "/3/2/1.png",
    "/osm/3/2/1.jpg",
    "/satellite/3/2/1.png",
    "/satellite/3/2/1.jpeg",
    "/other/3/2/1.png",
    "/osm/a/2/1.png",
    "/osm/3/2/1.png/extra",
    "osm/3/2/1.PNG",
])
def test_unknown_tile_paths_are_rejected(path: str):
    assert parse_tile_path(path) is None
