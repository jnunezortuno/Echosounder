"""Own each device in one acquisition thread; the GUI only sends queued commands."""
import queue
import threading

from PySide6.QtCore import QThread, Signal

from .device import Cancelled, SerialDevice, SimulationDevice
from .model import Settings
from .processing import process_trace


class AcquisitionWorker(QThread):
    connected = Signal(object, str)
    configured = Signal(object)
    frame_ready = Signal(object)
    busy_changed = Signal(bool)
    failed = Signal(str)

    def __init__(self, settings: Settings, simulated: bool, parent=None, device_factory=None):
        super().__init__(parent)
        self.settings = settings
        self.simulated = simulated
        self.commands = queue.Queue()
        self.shutdown = threading.Event()
        self.continuous = threading.Event()
        self.device_factory = device_factory or (SimulationDevice if simulated else SerialDevice)

    def submit(self, command: str, settings=None):
        self.commands.put((command, settings))

    def stop_acquisition(self):
        # Complete the current frame to preserve serial framing. Stop is bounded by the read timeout.
        self.continuous.clear()
        self.submit("stop")

    def disconnect_device(self):
        self.shutdown.set()
        self.continuous.clear()

    def run(self):
        device = self.device_factory(self.settings, self.shutdown)
        try:
            self.settings, version = device.open()
            if self.shutdown.is_set():
                return
            self.connected.emit(self.settings, version)
            while not self.shutdown.is_set():
                try:
                    command, settings = self.commands.get(timeout=0.01 if self.continuous.is_set() else 0.05)
                except queue.Empty:
                    command, settings = None, None
                if command == "configure":
                    self.settings = device.configure(settings)
                    self.configured.emit(self.settings)
                elif command == "continuous":
                    self.continuous.set()
                    self.busy_changed.emit(True)
                elif command == "stop":
                    self.continuous.clear()
                    self.busy_changed.emit(False)
                elif command == "single":
                    self.busy_changed.emit(True)
                if command == "single" or self.continuous.is_set():
                    raw = device.acquire()
                    frame = process_trace(raw, self.settings, simulated=device.simulated)
                    if not self.shutdown.is_set():
                        self.frame_ready.emit(frame)
                    if command == "single":
                        self.busy_changed.emit(False)
                    elif self.shutdown.wait(0.03):
                        break
        except Cancelled:
            pass
        except Exception as exc:
            # A failed transaction may leave a partial packet: close instead of blindly retrying.
            self.failed.emit(str(exc) or type(exc).__name__)
        finally:
            try:
                device.close()
            except Exception as exc:
                self.failed.emit(f"Error al cerrar el puerto: {exc}")
