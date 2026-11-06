"""Five-byte Echosounder protocol reconstructed from the supplied C++ objects."""
from dataclasses import replace
import struct
import threading
import time

import numpy as np
import serial
from serial.tools import list_ports

from .model import GAINS, SAMPLE_RATE, SAMPLES, Settings
from .processing import adc_full_scale


class ProtocolError(RuntimeError):
    pass


class Cancelled(RuntimeError):
    pass


def available_ports():
    return sorted(list_ports.comports(), key=lambda p: ("ST" not in (p.manufacturer or ""), p.device))


class SerialDevice:
    simulated = False

    def __init__(self, settings: Settings, cancel: threading.Event, serial_factory=serial.Serial):
        self.settings = settings
        self.cancel = cancel
        self.serial_factory = serial_factory
        self.port = None

    def open(self):
        if not self.settings.port:
            raise ValueError("Selecciona un puerto serie")
        try:
            self.port = self.serial_factory(
                port=self.settings.port, baudrate=self.settings.baudrate,
                bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                stopbits=self.settings.stopbits, timeout=0.05,
                write_timeout=self.settings.timeout, xonxoff=False, rtscts=False, dsrdtr=False)
            self.port.reset_input_buffer()
            self._exchange(0)
            response = self._exchange(5)
            # Original client skips payload byte 0, and reads the three following bytes.
            version = ".".join(str(v) for v in response[2:5])
            confirmed = self.configure(self.settings)
            return confirmed, f"v{version}"
        except Exception:
            self.close()
            raise

    def _write(self, packet: bytes):
        deadline = time.monotonic() + self.settings.timeout
        offset = 0
        while offset < len(packet):
            if self.cancel.is_set():
                raise Cancelled()
            if time.monotonic() >= deadline:
                raise ProtocolError("Tiempo agotado al enviar la orden")
            written = self.port.write(packet[offset:])
            if not written:
                raise ProtocolError("El puerto no aceptó la orden completa")
            offset += written

    def _read_exact(self, count: int) -> bytes:
        deadline = time.monotonic() + self.settings.timeout
        result = bytearray()
        while len(result) < count:
            if self.cancel.is_set():
                raise Cancelled()
            if time.monotonic() >= deadline:
                raise ProtocolError(f"Respuesta incompleta: {len(result)} de {count} bytes")
            result.extend(self.port.read(count - len(result)))
        return bytes(result)

    def _exchange(self, command: int, value=0) -> bytes:
        self._write(struct.pack("<Bi", command, value))
        response = self._read_exact(5)
        if response[0] != command:
            raise ProtocolError(f"Respuesta inesperada: {response[0]:02X}; se esperaba {command:02X}")
        return response

    def configure(self, settings: Settings) -> Settings:
        if (settings.port, settings.baudrate, settings.stopbits) != (
                self.settings.port, self.settings.baudrate, self.settings.stopbits):
            raise ValueError("Desconecta antes de cambiar los ajustes del puerto")
        values = {}
        for command, field in ((3, "delay_us"), (4, "cycles"), (2, "repetitions"), (6, "gain")):
            response = self._exchange(command, getattr(settings, field))
            values[field] = response[1] if command == 6 else struct.unpack("<i", response[1:])[0]
        # Validation also rejects impossible firmware confirmations.
        self.settings = replace(settings, **values)
        return self.settings

    def acquire(self) -> np.ndarray:
        self._write(b"\x01\x00\x00\x00\x00")
        return np.frombuffer(self._read_exact(SAMPLES * 4), dtype="<i4").copy()

    def close(self):
        if self.port is not None:
            self.port.close()
            self.port = None


class SimulationDevice:
    simulated = True

    def __init__(self, settings: Settings, cancel: threading.Event, seed=None):
        self.settings = settings
        self.cancel = cancel
        self.rng = np.random.default_rng(seed)
        self.sequence = 0

    def open(self):
        return self.settings, "Simulador 1.0"

    def configure(self, settings: Settings) -> Settings:
        self.settings = settings
        return settings

    def acquire(self) -> np.ndarray:
        if self.cancel.wait(0.07):
            raise Cancelled()
        s = self.settings
        time_s = (s.delay_us + np.arange(SAMPLES) * 1e6 / SAMPLE_RATE) * 1e-6
        carrier = 400_000
        voltage = self.rng.normal(0, 0.012 / np.sqrt(s.repetitions), SAMPLES)
        movement = 0.008 * np.sin(self.sequence / 16)
        for depth, amplitude, width in ((0.08 + movement, 0.65, 2e-6), (0.19, 0.28, 4e-6)):
            center = 2 * depth / s.sound_speed
            width *= np.sqrt(s.cycles / 3)
            pulse = np.exp(-0.5 * ((time_s - center) / width) ** 2)
            voltage += amplitude * pulse * np.sin(2 * np.pi * carrier * (time_s - center))
        voltage *= GAINS[s.gain] / 40
        full_scale = adc_full_scale(s.repetitions)
        raw = np.clip(np.rint((0.5 + voltage / 3.3) * full_scale), 0, full_scale).astype(np.int32)
        self.sequence += 1
        return raw

    def close(self):
        pass
