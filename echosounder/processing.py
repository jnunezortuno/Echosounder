"""Numerical processing, independent of Qt and the serial transport."""
from datetime import datetime, timezone

import numpy as np

from .model import FFT_SIZE, SAMPLE_RATE, SAMPLES, Frame, Settings


def adc_full_scale(repetitions: int) -> int:
    # Preserve the normalization found in the original client, including non-powers of two.
    return (1 << (12 + (repetitions - 1).bit_length())) - 1


def analytic_envelope(signal: np.ndarray) -> np.ndarray:
    """Analytic signal magnitude, zero-padded to the next power of two."""
    n = 1 << (len(signal) - 1).bit_length()
    multiplier = np.zeros(n)
    multiplier[0] = 1
    multiplier[1:n // 2] = 2
    if n > 1:
        multiplier[n // 2] = 1
    return np.abs(np.fft.ifft(np.fft.fft(signal, n=n) * multiplier))[:len(signal)]


def process_trace(raw: np.ndarray, settings: Settings, *, simulated=False) -> Frame:
    raw = np.asarray(raw)
    if raw.shape != (SAMPLES,) or raw.dtype.kind not in "iu":
        raise ValueError(f"Se requieren {SAMPLES} muestras enteras")
    if raw.min() < np.iinfo(np.int32).min or raw.max() > np.iinfo(np.int32).max:
        raise ValueError("Muestra fuera del rango int32")
    raw = raw.astype(np.int32, copy=True)
    voltage = raw.astype(np.float64)
    voltage = (voltage - voltage.mean()) * 3.3 / adc_full_scale(settings.repetitions)
    time_us = settings.delay_us + np.arange(SAMPLES) * (1e6 / SAMPLE_RATE)
    spectrum = np.fft.rfft(voltage, n=FFT_SIZE)[:FFT_SIZE // 2]
    power = np.abs(spectrum) ** 2 / (FFT_SIZE / 2) ** 2
    # A finite display floor prevents log(0), without changing nonzero values above it.
    spectrum_db = 10 * np.log10(np.maximum(power, 1e-24))
    return Frame(raw, time_us, time_us * settings.sound_speed / 20000,
                 voltage, analytic_envelope(voltage),
                 np.fft.rfftfreq(FFT_SIZE, 1 / SAMPLE_RATE)[:FFT_SIZE // 2] / 1e6,
                 spectrum_db, settings, datetime.now(timezone.utc), simulated)
