import time
from typing import Callable

import pytest
from PySide6.QtCore import QCoreApplication, Qt

try:
    import PySide6.QtWebEngineWidgets  # noqa: F401  (must be imported before the app exists)
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover
    QApplication = None


@pytest.fixture(scope="session")
def qapp() -> QCoreApplication:
    existing = QCoreApplication.instance()
    if existing is not None:
        return existing
    if QApplication is None:
        return QCoreApplication([])
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    return QApplication([])


@pytest.fixture
def wait_until(qapp: QCoreApplication) -> Callable[..., bool]:
    def _wait(pred: Callable[[], bool], timeout: float = 5.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            qapp.processEvents()
            if pred():
                return True
            time.sleep(0.01)
        qapp.processEvents()
        return pred()

    return _wait
