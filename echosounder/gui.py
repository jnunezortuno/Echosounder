from pathlib import Path
import time

import numpy as np
from PySide6 import QtCore, QtWidgets as W
import pyqtgraph as pg

from .device import available_ports
from .export import export_csv
from .model import GAINS, HISTORY, SAMPLE_RATE, SAMPLES, Frame, Settings
from .worker import AcquisitionWorker

STYLE = """
QMainWindow, QWidget { background: #0c1423; color: #dce7f5; font-family: 'Segoe UI'; font-size: 13px; }
QLabel { background: transparent; }
QFrame#panel, QGroupBox { background: #121f32; border: 1px solid #25364e; border-radius: 10px; }
QGroupBox { margin-top: 14px; padding: 14px 10px 10px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; color: #8ca6c5; }
QLabel#title { font-size: 25px; font-weight: 700; color: #f3f7fc; }
QLabel#muted { color: #8ca6c5; }
QLabel#metric { font-size: 23px; font-weight: 600; color: #5eead4; }
QLabel#badge { color: #5eead4; background: #153334; border-radius: 8px; padding: 8px 14px; }
QPushButton { background: #20324b; border: 1px solid #324963; padding: 9px 13px; border-radius: 6px; }
QPushButton:hover { background: #2a4361; }
QPushButton:checked { background: #175d60; border-color: #39c9b7; color: #ecfffc; }
QPushButton#primary { background: #21786e; border-color: #38af9c; font-weight: 600; }
QPushButton#stop { background: #673c31; border-color: #a1644d; }
QPushButton:disabled { color: #53657c; background: #142034; border-color: #223248; }
QPushButton#primary:disabled, QPushButton#stop:disabled { color: #53657c; background: #142034; border-color: #223248; }
QComboBox, QSpinBox, QDoubleSpinBox { background: #0c1728; border: 1px solid #31465e;
    border-radius: 5px; padding: 6px; min-height: 19px; }
QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled { color: #687c95; }
QComboBox QAbstractItemView { background: #15263e; selection-background-color: #24655e; }
QStatusBar { color: #8ca6c5; border-top: 1px solid #25364e; }
QSlider::groove:horizontal { background: #263d54; height: 5px; border-radius: 2px; }
QSlider::handle:horizontal { background: #53d8c2; width: 12px; margin: -4px 0; border-radius: 5px; }
"""


class MainWindow(W.QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.connected = False
        self.confirmed_settings = None
        self.busy = False
        self.pending = False
        self.closing = False
        self.auto_start = False
        self.last_frame = None
        self.frame_count = 0
        self.last_frame_time = None
        self.history = np.zeros((SAMPLES, HISTORY), dtype=np.float32)
        self.setWindowTitle("Echosounder · CUD-ENM")
        self.resize(1320, 850)
        self.setMinimumSize(980, 720)
        self.setStyleSheet(STYLE)
        pg.setConfigOptions(antialias=True, background="#0c1728", foreground="#99aec9")
        self._build_ui()
        self.refresh_ports()
        self._update_controls()

    def _build_ui(self):
        central = W.QWidget()
        self.setCentralWidget(central)
        outer = W.QVBoxLayout(central)
        outer.setContentsMargins(24, 20, 24, 14)
        outer.setSpacing(16)
        header = W.QHBoxLayout()
        brand = W.QVBoxLayout()
        brand.addWidget(self._label("ECHOSOUNDER CUD-ENM", "title"))
        brand.addWidget(self._label("Adquisición y visualización de ecos", "muted"))
        header.addLayout(brand)
        header.addStretch()
        self.badge = self._label("DESCONECTADO", "badge")
        header.addWidget(self.badge)
        outer.addLayout(header)
        body = W.QHBoxLayout()
        body.setSpacing(18)
        outer.addLayout(body, 1)

        sidebar = W.QWidget()
        sidebar.setFixedWidth(290)
        side = W.QVBoxLayout(sidebar)
        side.setContentsMargins(0, 0, 0, 0)
        connection = W.QGroupBox("CONEXIÓN")
        form = W.QFormLayout(connection)
        self.source = W.QComboBox()
        self.source.addItem("Simulación", True)
        self.source.addItem("Ecosonda por puerto serie", False)
        self.source.currentIndexChanged.connect(self._update_controls)
        form.addRow("Fuente", self.source)
        port_row = W.QWidget()
        port_layout = W.QHBoxLayout(port_row)
        port_layout.setContentsMargins(0, 0, 0, 0)
        self.port = W.QComboBox()
        self.port.setEditable(True)
        self.refresh_button = W.QPushButton("↻")
        self.refresh_button.setFixedWidth(34)
        self.refresh_button.setToolTip("Actualizar puertos")
        self.refresh_button.clicked.connect(self.refresh_ports)
        port_layout.addWidget(self.port, 1)
        port_layout.addWidget(self.refresh_button)
        form.addRow("Puerto", port_row)
        self.baud = self._spin(1, 1_000_000_000, 921600)
        form.addRow("Baudios", self.baud)
        self.stopbits = W.QComboBox()
        for v in (1, 1.5, 2):
            self.stopbits.addItem(str(v), v)
        form.addRow("Bits de parada", self.stopbits)
        self.connect_button = W.QPushButton("Conectar")
        self.connect_button.setObjectName("primary")
        self.connect_button.clicked.connect(self.connect_device)
        self.disconnect_button = W.QPushButton("Desconectar")
        self.disconnect_button.clicked.connect(self.disconnect_device)
        form.addRow(self.connect_button, self.disconnect_button)
        side.addWidget(connection)

        acquisition = W.QGroupBox("ADQUISICIÓN")
        form = W.QFormLayout(acquisition)
        self.delay = self._spin(0, 1000, 50)
        self.delay.setSuffix(" µs")
        self.delay.setToolTip(
            "Retardo de inicio de la ventana de adquisición, en microsegundos. "
            "Desplaza el eje de tiempo y la profundidad estimada."
        )
        self.repetitions = self._spin(1, 256, 1)
        self.repetitions.setToolTip(
            "Número de repeticiones configurado por traza. Este valor interviene en la escala de amplitud mostrada."
        )
        self.cycles = self._spin(1, 16, 3)
        self.cycles.setToolTip(
            "Ciclos del pulso transmitido por repetición."
        )
        self.gain = W.QComboBox()
        for code, multiplier in GAINS.items():
            self.gain.addItem(f"×{multiplier:g}", code)
        self.gain.setCurrentIndex(self.gain.findData(0x90))
        self.gain.setToolTip(
            "Ganancia configurada en el instrumento. El voltaje mostrado no se corrige por esta ganancia."
        )

        self.sound_speed = W.QDoubleSpinBox()
        self.sound_speed.setRange(300, 5000)
        self.sound_speed.setValue(1500)
        self.sound_speed.setSuffix(" m/s")
        self.sound_speed.setDecimals(1)
        self.sound_speed.setToolTip(
            "Velocidad del sonido asumida en el medio."
        )
        for label, widget in (("Inicio", self.delay), ("Repeticiones", self.repetitions),
                              ("Ciclos", self.cycles), ("Ganancia", self.gain),
                              ("Velocidad sonido", self.sound_speed)):
            form.addRow(label, widget)
        self.apply_button = W.QPushButton("Aplicar ajustes")
        self.apply_button.setToolTip(
            "Envía los ajustes de adquisición al instrumento. La aplicación reinicia el "
            "historial al confirmarlos."
        )
        self.apply_button.clicked.connect(self.apply_settings)
        form.addRow(self.apply_button)
        side.addWidget(acquisition)
        side.addStretch()
        self.source_note = self._label("La simulación genera dos ecos y ruido.", "muted")
        self.source_note.setWordWrap(True)
        side.addWidget(self.source_note)
        side.addWidget(self._label("1.700 muestras · 5 MHz\nHistorial de 256 trazas", "muted"))
        body.addWidget(sidebar)

        right = W.QVBoxLayout()
        metrics = W.QHBoxLayout()
        self.metrics = {}
        for key, title, initial in (("frames", "TRAZAS", "0"), ("fps", "CADENCIA", "— fps"),
                                     ("peak", "PICO DE ENVOLVENTE", "— V")):
            card = W.QFrame()
            card.setObjectName("panel")
            layout = W.QVBoxLayout(card)
            layout.addWidget(self._label(title, "muted"))
            value = self._label(initial, "metric")
            layout.addWidget(value)
            metrics.addWidget(card)
            self.metrics[key] = value
        right.addLayout(metrics)
        buttons = W.QHBoxLayout()
        self.single_button = W.QPushButton("Adquirir una traza")
        self.single_button.clicked.connect(lambda: self.acquire(False))
        self.run_button = W.QPushButton("Adquisición continua")
        self.run_button.setObjectName("primary")
        self.run_button.clicked.connect(lambda: self.acquire(True))
        self.stop_button = W.QPushButton("Detener")
        self.stop_button.setObjectName("stop")
        self.stop_button.clicked.connect(self.stop_acquisition)
        for button in (self.single_button, self.run_button, self.stop_button):
            buttons.addWidget(button)
        buttons.addStretch()
        right.addLayout(buttons)
        tabs = W.QHBoxLayout()
        self.view_buttons = []
        self.view_group = W.QButtonGroup(self)
        self.view_group.setExclusive(True)
        for i, title in enumerate(("Señal", "Espectro", "Mapa de profundidad")):
            button = W.QPushButton(title)
            button.setCheckable(True)
            self.view_group.addButton(button, i)
            self.view_buttons.append(button)
            tabs.addWidget(button)
        self.view_buttons[0].setChecked(True)
        self.view_group.idClicked.connect(self.set_view)
        tabs.addStretch()
        self.zoom_button = W.QPushButton("Restablecer zoom")
        self.zoom_button.clicked.connect(self.reset_zoom)
        tabs.addWidget(self.zoom_button)
        right.addLayout(tabs)
        self.plots = W.QStackedWidget()
        self.wave = pg.PlotWidget()
        self.wave.setLabel("bottom", "Tiempo", units="µs")
        self.wave.setLabel("left", "Señal", units="V")
        self.wave.addLegend(offset=(12, 12))
        self.signal_curve = self.wave.plot(pen=pg.mkPen("#4ddfc2", width=1.4), name="Señal")
        self.envelope_curve = self.wave.plot(pen=pg.mkPen("#ffbe76", width=1.8), name="Envolvente")
        self.spectrum = pg.PlotWidget()
        self.spectrum.setLabel("bottom", "Frecuencia", units="MHz")
        self.spectrum.setLabel("left", "Nivel espectral", units="dBV")
        self.spectrum_curve = self.spectrum.plot(pen=pg.mkPen("#83b5ff", width=1.6))
        self.map_plot = pg.PlotWidget()
        self.map_plot.setLabel("bottom", "Antigüedad de la traza (0 = más reciente)")
        self.map_plot.setLabel("left", "Profundidad", units="cm")
        self.map_plot.getViewBox().invertY(True)
        self.map_image = pg.ImageItem(axisOrder="row-major")
        self.map_image.setColorMap(pg.colormap.get("viridis"))
        self.map_plot.addItem(self.map_image)
        for plot in (self.wave, self.spectrum, self.map_plot):
            plot.showGrid(x=True, y=True, alpha=0.13)
            plot.getPlotItem().hideButtons()
            self.plots.addWidget(plot)
        right.addWidget(self.plots, 1)
        self.map_controls = W.QWidget()
        levels = W.QHBoxLayout(self.map_controls)
        levels.setContentsMargins(0, 0, 0, 0)
        levels.addWidget(self._label("Rango de color", "muted"))
        self.level_min = W.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.level_min.setRange(0, 99)
        self.level_max = W.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.level_max.setRange(1, 100)
        self.level_max.setValue(100)
        for title, slider in (("Mín.", self.level_min), ("Máx.", self.level_max)):
            levels.addWidget(W.QLabel(title))
            levels.addWidget(slider)
            slider.valueChanged.connect(self.update_levels)
        right.addWidget(self.map_controls)
        footer = W.QHBoxLayout()
        self.message = self._label("Conecta la simulación o selecciona un puerto para comenzar.", "muted")
        self.message.setWordWrap(True)
        self.message.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        footer.addWidget(self.message, 1)
        self.export_button = W.QPushButton("Exportar traza CSV")
        self.export_button.clicked.connect(self.save_trace)
        footer.addWidget(self.export_button)
        right.addLayout(footer)
        body.addLayout(right, 1)
        self.statusBar().showMessage("Python · Qt 6 · NumPy")
        for widget in (self.delay, self.repetitions, self.cycles, self.sound_speed):
            widget.valueChanged.connect(self._update_controls)
        self.gain.currentIndexChanged.connect(self._update_controls)
        self.set_view(0)

    @staticmethod
    def _label(text, name):
        label = W.QLabel(text)
        label.setObjectName(name)
        return label

    @staticmethod
    def _spin(low, high, initial):
        spin = W.QSpinBox()
        spin.setRange(low, high)
        spin.setValue(initial)
        return spin

    @QtCore.Slot()
    def refresh_ports(self):
        old = self.port.currentText()
        self.port.clear()
        try:
            ports = available_ports()
        except Exception as exc:
            self.show_error(str(exc))
            return
        for port in ports:
            self.port.addItem(port.device)
        if old:
            self.port.setCurrentText(old)

    def settings_from_ui(self):
        return Settings(port=self.port.currentText().strip(), baudrate=self.baud.value(),
                        stopbits=self.stopbits.currentData(), delay_us=self.delay.value(),
                        repetitions=self.repetitions.value(), cycles=self.cycles.value(),
                        gain=self.gain.currentData(), sound_speed=self.sound_speed.value())

    def settings_to_ui(self, settings):
        self.delay.setValue(settings.delay_us)
        self.repetitions.setValue(settings.repetitions)
        self.cycles.setValue(settings.cycles)
        self.gain.setCurrentIndex(self.gain.findData(settings.gain))
        self.sound_speed.setValue(settings.sound_speed)

    @QtCore.Slot()
    def connect_device(self):
        if self.worker is not None:
            return
        try:
            settings = self.settings_from_ui()
            simulated = self.source.currentData()
            if not simulated and not settings.port:
                raise ValueError("Selecciona un puerto serie antes de conectar.")
            self.worker = AcquisitionWorker(settings, simulated, self)
            self.worker.connected.connect(self.on_connected)
            self.worker.configured.connect(self.on_configured)
            self.worker.frame_ready.connect(self.on_frame)
            self.worker.busy_changed.connect(self.on_busy)
            self.worker.failed.connect(self.show_error)
            self.worker.finished.connect(self.on_finished)
            self.pending = True
            self.badge.setText("CONECTANDO…")
            self._update_controls()
            self.worker.start()
        except Exception as exc:
            self.show_error(str(exc))

    @QtCore.Slot(object, str)
    def on_connected(self, settings, version):
        if self.closing or self.worker.shutdown.is_set():
            return
        self.connected = True
        self.pending = False
        self.confirmed_settings = settings
        self.settings_to_ui(settings)
        self.clear_history()
        self.badge.setText("SIMULACIÓN" if self.worker.simulated else f"CONECTADO · {settings.port}")
        self.message.setText(f"{version} · {'Datos simulados' if self.worker.simulated else 'Dispositivo conectado'}")
        self.message.setStyleSheet("")
        self._update_controls()
        if self.auto_start:
            self.auto_start = False
            self.acquire(True)

    @QtCore.Slot()
    def disconnect_device(self):
        if self.worker:
            self.pending = True
            self.badge.setText("DESCONECTANDO…")
            self.worker.disconnect_device()
            self._update_controls()

    @QtCore.Slot()
    def apply_settings(self):
        if not self.connected or self.busy or self.pending:
            return
        try:
            self.pending = True
            self._update_controls()
            self.worker.submit("configure", self.settings_from_ui())
        except Exception as exc:
            self.pending = False
            self.show_error(str(exc))
            self._update_controls()

    @QtCore.Slot(object)
    def on_configured(self, settings):
        self.pending = False
        self.confirmed_settings = settings
        self.settings_to_ui(settings)
        self.clear_history()
        self.message.setText("Ajustes confirmados. Historial reiniciado.")
        self._update_controls()

    def acquire(self, continuously):
        if not self.connected or self.busy or self.pending:
            return
        if self.settings_from_ui() != self.confirmed_settings:
            self.message.setText("Aplica los ajustes modificados antes de adquirir.")
            return
        self.busy = True
        self._update_controls()
        self.worker.submit("continuous" if continuously else "single")

    @QtCore.Slot()
    def stop_acquisition(self):
        if self.worker:
            self.worker.stop_acquisition()
            self.stop_button.setEnabled(False)
            self.message.setText("Terminando la traza en curso…")

    @QtCore.Slot(bool)
    def on_busy(self, busy):
        self.busy = busy
        self._update_controls()
        if not busy:
            self.message.setText("Adquisición detenida. Puedes modificar los ajustes o exportar la última traza.")

    @QtCore.Slot(object)
    def on_frame(self, frame: Frame):
        if self.closing:
            return
        self.last_frame = frame
        self.history[:, 1:] = self.history[:, :-1].copy()
        self.history[:, 0] = np.sqrt(frame.envelope)
        self.frame_count += 1
        now = time.monotonic()
        if self.last_frame_time is not None:
            self.metrics["fps"].setText(f"{1 / max(now - self.last_frame_time, 1e-6):.1f} fps")
        self.last_frame_time = now
        self.metrics["frames"].setText(str(self.frame_count))
        self.metrics["peak"].setText(f"{frame.envelope.max():.3f} V")
        self.render_frame()
        self.export_button.setEnabled(True)

    def render_frame(self):
        frame = self.last_frame
        if frame is None:
            return
        index = self.plots.currentIndex()
        if index == 0:
            self.signal_curve.setData(frame.time_us, frame.voltage)
            self.envelope_curve.setData(frame.time_us, frame.envelope)
        elif index == 1:
            self.spectrum_curve.setData(frame.frequency_mhz, frame.spectrum_db)
        else:
            self.map_image.setImage(self.history, autoLevels=False)
            step = frame.settings.sound_speed / (2 * SAMPLE_RATE) * 100
            self.map_image.setRect(QtCore.QRectF(-0.5, frame.depth_cm[0] - step / 2,
                                               HISTORY, SAMPLES * step))
            self.update_levels()

    @QtCore.Slot(int)
    def set_view(self, index):
        self.plots.setCurrentIndex(index)
        self.view_buttons[index].setChecked(True)
        self.map_controls.setVisible(index == 2)
        self.render_frame()
        self.reset_zoom()

    @QtCore.Slot()
    def reset_zoom(self):
        (self.wave, self.spectrum, self.map_plot)[self.plots.currentIndex()].enableAutoRange()

    @QtCore.Slot()
    def update_levels(self):
        low, high = self.level_min.value(), self.level_max.value()
        if low >= high:
            if self.sender() is self.level_min:
                self.level_max.setValue(low + 1)
            else:
                self.level_min.setValue(high - 1)
            return
        factor = np.sqrt(1.65) / 100
        self.map_image.setLevels((low * factor, high * factor))

    def clear_history(self):
        self.history.fill(0)
        self.last_frame = None
        self.frame_count = 0
        self.last_frame_time = None
        self.signal_curve.clear()
        self.envelope_curve.clear()
        self.spectrum_curve.clear()
        self.map_image.clear()
        self.metrics["frames"].setText("0")
        self.metrics["fps"].setText("— fps")
        self.metrics["peak"].setText("— V")

    @QtCore.Slot()
    def save_trace(self):
        frame = self.last_frame
        if frame is None:
            return
        path, _ = W.QFileDialog.getSaveFileName(self, "Guardar traza", "echosounder-trace.csv", "CSV (*.csv)")
        if path:
            try:
                export_csv(Path(path), frame)
                self.message.setText(f"Traza guardada: {path}")
            except Exception as exc:
                self.show_error(str(exc))

    @QtCore.Slot(str)
    def show_error(self, message):
        self.message.setText(f"Error: {message}")
        self.message.setStyleSheet("color: #ffad93;")

    @QtCore.Slot()
    def on_finished(self):
        worker = self.worker
        self.worker = None
        self.connected = self.busy = self.pending = False
        self.badge.setText("DESCONECTADO")
        self._update_controls()
        if worker:
            worker.deleteLater()
        if self.closing:
            self.close()

    def _update_controls(self):
        running = self.worker is not None
        editable = not self.busy and not self.pending and not self.closing
        dirty = self.connected and self.settings_from_ui() != self.confirmed_settings
        self.source.setEnabled(not running and not self.closing)
        serial_options = not running and not self.source.currentData() and not self.closing
        for widget in (self.port, self.refresh_button, self.baud, self.stopbits):
            widget.setEnabled(serial_options)
        for widget in (self.delay, self.repetitions, self.cycles, self.gain, self.sound_speed):
            widget.setEnabled(editable)
        self.connect_button.setEnabled(not running and not self.closing)
        self.disconnect_button.setEnabled(running and not self.pending and not self.closing)
        self.apply_button.setEnabled(self.connected and editable and dirty)
        self.apply_button.setText("Aplicar ajustes *" if dirty else "Aplicar ajustes")
        self.single_button.setEnabled(self.connected and editable and not dirty)
        self.run_button.setEnabled(self.connected and editable and not dirty)
        self.stop_button.setEnabled(self.connected and self.busy and not self.pending and not self.closing)
        self.export_button.setEnabled(self.last_frame is not None and not self.closing)
        self.source_note.setText("La simulación genera dos ecos y ruido."
            if self.source.currentData() else
            "Selecciona el puerto de la ecosonda. La frecuencia de muestreo prevista es 5 MHz.")

    def closeEvent(self, event):
        if self.worker is not None:
            self.closing = True
            self.worker.disconnect_device()
            self._update_controls()
            event.ignore()
        else:
            event.accept()
