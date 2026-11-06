import argparse
import os
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description="Echosounder Python")
    parser.add_argument("--simulate", action="store_true", help="Iniciar adquisición continua simulada")
    args = parser.parse_args(argv)
    # Select Qt 6 before importing pyqtgraph, even when PyQt5 is also installed.
    os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from .gui import MainWindow
    app = QApplication([sys.argv[0]])
    app.setApplicationName("Echosounder Python")
    app.setOrganizationName("Echosounder")
    window = MainWindow()
    window.show()
    if args.simulate:
        window.auto_start = True
        QTimer.singleShot(0, window.connect_device)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
