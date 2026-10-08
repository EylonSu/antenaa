from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from platformdirs import user_config_dir

APP_NAME = "AntennaTracker"
CONFIG_FILE = "config.json"


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
    known = {f.name for f in fields(AppConfig)}
    return AppConfig(**{k: v for k, v in data.items() if k in known})


def save_config(config: AppConfig, path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
