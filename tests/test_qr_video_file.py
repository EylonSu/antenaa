"""End to end: generated mp4 of QR codes -> --video-file playback -> QrDecoder -> QrVideoSource."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("segno")
pytest.importorskip("zxingcpp")
pytest.importorskip("PySide6.QtWebEngineWidgets")

from antenna_tracker.app import parse_args  # noqa: E402
from antenna_tracker.config import AppConfig  # noqa: E402
from antenna_tracker.hardware import fake_turret  # noqa: E402
from antenna_tracker.hardware.turret_client import TurretClient  # noqa: E402
from antenna_tracker.ui.main_window import SOURCE_QR, MainWindow  # noqa: E402
from antenna_tracker.video.capture import set_video_file_override  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _gen():
    spec = importlib.util.spec_from_file_location("make_qr_video", ROOT / "scripts" / "make_qr_video.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def qr_mp4(qapp, tmp_path_factory):
    gen = _gen()
    path = tmp_path_factory.mktemp("video") / "qr.mp4"
    if not gen.write_qr_video(path, gen.demo_payloads(seconds=8, fps=10, period_s=120), fps=10, timeout_s=60):
        pytest.skip("no H.264 encoder available in this Qt build / environment")
    return path


def test_video_file_feeds_qr_source(qapp, qr_mp4, wait_until, monkeypatch):
    monkeypatch.setattr("antenna_tracker.ui.main_window.save_config", lambda *_: None)
    args = parse_args(["--dev", "--video-file", str(qr_mp4)])
    set_video_file_override(args.video_file)
    turret = TurretClient(heartbeat_s=0.1, reply_timeout_s=0.3, reconnect_s=0.1, ready_timeout_s=0.3)
    config = AppConfig(utm_easting="667000", utm_northing="550500", antenna_alt_amsl=30.0,
                       ref_azimuth=45.0, port_device=fake_turret.FAKE_PORT)
    win = MainWindow(config, turret, dev_mode=True)
    try:
        win.show()
        assert win.source_kind == SOURCE_QR
        src = win.qr_source
        lost = []
        src.gps_lost.connect(lambda: lost.append(True))
        assert wait_until(lambda: src.latest() is not None, timeout=20), "no QR position decoded from the file"
        assert win.serial_label.text() == "DRN-4521"
        first = src.latest()
        assert 31.9 < first.lat < 32.3 and 34.6 < first.lon < 35.0
        assert wait_until(lambda: src.latest().t != first.t and (src.latest().lat, src.latest().lon)
                          != (first.lat, first.lon), timeout=10)
        assert wait_until(lambda: bool(lost), timeout=15), "GPS dropout in the clip was not detected"
        assert wait_until(lambda: win._qr_rate > 0, timeout=5)
    finally:
        win.shutdown()
        win.close()
        turret.close()
        set_video_file_override(None)
