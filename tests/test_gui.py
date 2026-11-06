import time

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from echosounder.gui import MainWindow


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def wait_until(app, condition, timeout=4):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents()
        if condition():
            return
        time.sleep(0.01)
    raise AssertionError("La operación de la interfaz no terminó a tiempo")


@pytest.fixture
def window(app):
    window = MainWindow()
    window.show()
    app.processEvents()
    yield window
    window.close()
    wait_until(app, lambda: window.worker is None)
    window.deleteLater()
    app.processEvents()


def test_simulation_views_settings_stop_and_disconnect(app, window):
    assert not window.single_button.isEnabled()
    window.connect_device()
    wait_until(app, lambda: window.connected)
    window.acquire(False)
    wait_until(app, lambda: window.last_frame is not None and not window.busy)
    assert window.last_frame.simulated
    assert len(window.signal_curve.getData()[0]) == 1700
    for view in (1, 2, 0):
        window.set_view(view)
        app.processEvents()
    assert len(window.spectrum_curve.getData()[0]) == 512
    assert window.map_image.image.shape == (1700, 256)
    assert np.max(window.history[:, 0]) > 0
    window.delay.setValue(100)
    assert not window.single_button.isEnabled()
    assert window.apply_button.isEnabled()
    assert window.apply_button.text().endswith("*")
    window.apply_settings()
    wait_until(app, lambda: not window.pending)
    assert window.last_frame is None
    assert not window.export_button.isEnabled()
    window.acquire(True)
    wait_until(app, lambda: window.frame_count >= 3)
    assert window.last_frame.time_us[0] == 100
    assert not window.apply_button.isEnabled()
    window.stop_acquisition()
    wait_until(app, lambda: not window.busy)
    count = window.frame_count
    for _ in range(20):
        app.processEvents()
        time.sleep(0.01)
    assert window.frame_count == count
    window.disconnect_device()
    wait_until(app, lambda: window.worker is None)
    assert not window.connected
    assert window.connect_button.isEnabled()


def test_no_ports_and_no_accidental_hardware_connection(app, monkeypatch):
    monkeypatch.setattr("echosounder.gui.available_ports", lambda: [])
    window = MainWindow()
    window.source.setCurrentIndex(1)
    assert window.port.count() == 0
    window.connect_device()
    assert window.worker is None
    assert "Selecciona un puerto" in window.message.text()
    window.close()
    window.deleteLater()


def test_close_during_continuous_acquisition(app, window):
    window.connect_device()
    wait_until(app, lambda: window.connected)
    window.acquire(True)
    wait_until(app, lambda: window.frame_count >= 1)
    window.close()
    wait_until(app, lambda: window.worker is None)
    assert not window.isVisible()
