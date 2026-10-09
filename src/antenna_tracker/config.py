from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from platformdirs import user_config_dir

APP_NAME = "AntennaTracker"
CONFIG_FILE = "config.json"


@dataclass
class QrFields:
    """0-based indices into the pipe-separated QR payload."""
    serial: int = 0
    lat: int = 1
    lon: int = 2
    rel_alt: int = 6
    heading: int | None = 5
    home_dist: int | None = 12
    antenna_dist: int | None = 13


# (lat_min, lat_max, lon_min, lon_max): roughly Israel
ISRAEL_BOUNDS: tuple[float, float, float, float] = (29.3, 33.5, 34.0, 36.0)


@dataclass
class AppConfig:
    port_device: str | None = None
    port_vid: int | None = None
    port_pid: int | None = None
    port_serial_number: str | None = None
    video_device_id: str | None = None
    utm_easting: str = ""
    utm_northing: str = ""
    antenna_alt_amsl: float = 0.0
    ref_azimuth: float = 0.0
    ref_is_magnetic: bool = False
    declination_deg: float = 5.0
    update_interval_s: float = 1.0
    stale_timeout_s: float = 5.0
    developer_mode: bool = False
    takeoff_near_antenna: bool = True
    takeoff_alt_amsl: float = 0.0
    qr_fields: QrFields = field(default_factory=QrFields)
    qr_max_speed_mps: float = 60.0
    qr_bounds: tuple[float, float, float, float] = ISRAEL_BOUNDS
    qr_gps_debounce: int = 3
    qr_decode_fps: float = 10.0
    qr_roi: tuple[float, float] = (0.25, 0.35)  # fraction of width, height from top-left
    map_basemap: str = "osm"

    @property
    def effective_takeoff_alt_amsl(self) -> float:
        return self.antenna_alt_amsl if self.takeoff_near_antenna else self.takeoff_alt_amsl

    @property
    def ref_azimuth_true(self) -> float:
        az = self.ref_azimuth + (self.declination_deg if self.ref_is_magnetic else 0.0)
        return az % 360.0


def config_path() -> Path:
    return Path(user_config_dir(APP_NAME, appauthor=False)) / CONFIG_FILE


def load_config(path: Path | None = None) -> AppConfig:
    path = path or config_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return AppConfig()
    if not isinstance(data, dict):
        return AppConfig()
    known = {f.name for f in fields(AppConfig)}
    kw = {k: v for k, v in data.items() if k in known}
    qf = kw.pop("qr_fields", None)
    for k in ("qr_bounds", "qr_roi"):
        if isinstance(kw.get(k), list):
            kw[k] = tuple(kw[k])
    cfg = AppConfig(**kw)
    if isinstance(qf, dict):
        names = {f.name for f in fields(QrFields)}
        cfg.qr_fields = QrFields(**{k: v for k, v in qf.items() if k in names})
    if cfg.map_basemap not in ("osm", "satellite"):
        cfg.map_basemap = "osm"
    return cfg


def save_config(config: AppConfig, path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
