from dataclasses import dataclass
from datetime import datetime

import numpy as np
from numpy.typing import NDArray

SAMPLES = 1700
SAMPLE_RATE = 5_000_000
HISTORY = 256
FFT_SIZE = 1024
GAINS = {0xC8: 0.2, 0x80: 1, 0xC0: 10, 0xA0: 20, 0xE0: 30,
         0x90: 40, 0xD0: 60, 0xB0: 80, 0xF0: 120, 0x88: 157}


@dataclass(frozen=True)
class Settings:
    port: str = ""
    baudrate: int = 921600
    stopbits: float = 1.0
    delay_us: int = 50
    repetitions: int = 1
    cycles: int = 3
    gain: int = 0x90
    sound_speed: float = 1500.0
    timeout: float = 1.0

    def __post_init__(self):
        for name, low, high in (("baudrate", 1, 1_000_000_000), ("delay_us", 0, 1000),
                                ("repetitions", 1, 256), ("cycles", 1, 16)):
            value = getattr(self, name)
            if not isinstance(value, int) or not low <= value <= high:
                raise ValueError(f"{name}: debe ser un entero entre {low} y {high}")
        if self.stopbits not in (1, 1.5, 2):
            raise ValueError("Bits de parada: elige 1, 1.5 o 2")
        if self.gain not in GAINS:
            raise ValueError("Código de ganancia desconocido")
        if not 300 <= self.sound_speed <= 5000:
            raise ValueError("Velocidad del sonido fuera de rango")
        if not 0.1 <= self.timeout <= 30:
            raise ValueError("Tiempo de espera fuera de rango")


@dataclass(frozen=True)
class Frame:
    raw: NDArray[np.int32]
    time_us: NDArray[np.float64]
    depth_cm: NDArray[np.float64]
    voltage: NDArray[np.float64]
    envelope: NDArray[np.float64]
    frequency_mhz: NDArray[np.float64]
    spectrum_db: NDArray[np.float64]
    settings: Settings
    acquired_at: datetime
    simulated: bool
