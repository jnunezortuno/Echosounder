"""Render the three simulated views offscreen; no serial device is opened."""
import os
from pathlib import Path
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from echosounder.gui import MainWindow


def main():
    output = Path(__file__).resolve().parent.parent / "docs" / "images"
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    # The offscreen platform has no Windows font database; use installed system fonts.
    if sys.platform == "win32":
        fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "seguisym.ttf"):
            QFontDatabase.addApplicationFont(str(fonts / name))
    window = MainWindow()
    window.auto_start = True
    window.show()
    timer = QTimer()
    stopping = False
    captured = False

    def inspect():
        nonlocal stopping, captured
        if window.frame_count < 30:
            return
        if not stopping:
            stopping = True
            window.stop_acquisition()
        if window.busy or captured:
            return
        captured = True
        timer.stop()
        for index, name in enumerate(("wave", "spectrum", "map")):
            window.set_view(index)
            app.processEvents()
            filename = output / f"python-{name}.png"
            if not window.grab().save(str(filename)):
                raise RuntimeError(f"No se pudo guardar {filename}")
            print(filename, flush=True)
        window.close()

    timer.timeout.connect(inspect)
    timer.start(50)
    QTimer.singleShot(0, window.connect_device)
    QTimer.singleShot(20_000, window.close)
    app.exec()
    if not captured:
        raise RuntimeError("No se adquirieron las trazas necesarias para la vista previa")


if __name__ == "__main__":
    main()
