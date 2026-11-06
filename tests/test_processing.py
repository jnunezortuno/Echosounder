from dataclasses import replace

import numpy as np
import pytest

from echosounder.export import export_csv
from echosounder.model import SAMPLE_RATE, SAMPLES, Settings
from echosounder.processing import adc_full_scale, analytic_envelope, process_trace


def test_constant_trace_has_zero_signal_and_finite_spectrum():
    frame = process_trace(np.full(SAMPLES, 2048, dtype=np.int32), Settings())
    assert np.all(frame.voltage == 0)
    assert np.all(frame.envelope == 0)
    assert np.all(np.isfinite(frame.spectrum_db))
    assert len(frame.spectrum_db) == 512
    assert frame.time_us[0] == 50
    assert frame.time_us[-1] == pytest.approx(389.8)
    assert frame.depth_cm[[0, -1]].tolist() == pytest.approx([3.75, 29.235])


def test_tone_has_correct_fft_frequency_and_level():
    # Tone exactly at bin 80 of the 1024-point FFT; full trace mean is separately removed.
    frequency = 80 * SAMPLE_RATE / 1024
    raw = np.rint(2048 + 600 * np.sin(2 * np.pi * frequency * np.arange(SAMPLES) / SAMPLE_RATE)).astype(np.int32)
    frame = process_trace(raw, Settings())
    peak = np.argmax(frame.spectrum_db[1:]) + 1
    assert peak == 80
    assert frame.frequency_mhz[peak] == pytest.approx(frequency / 1e6)
    assert frame.spectrum_db[peak] == pytest.approx(20 * np.log10(600 * 3.3 / 4095), abs=0.01)


def test_analytic_envelope_preserves_sinusoid_amplitude():
    tone = 0.4 * np.cos(2 * np.pi * 50 * np.arange(2048) / 2048)
    np.testing.assert_allclose(analytic_envelope(tone), 0.4, atol=1e-12)


@pytest.mark.parametrize("repetitions,full_scale", [(1, 4095), (2, 8191), (3, 16383), (256, 1048575)])
def test_original_accumulation_scaling(repetitions, full_scale):
    assert adc_full_scale(repetitions) == full_scale


@pytest.mark.parametrize("raw", [np.zeros(3, dtype=int), np.zeros(SAMPLES),
                                 np.full(SAMPLES, 2**40, dtype=np.int64)])
def test_rejects_malformed_trace(raw):
    with pytest.raises(ValueError):
        process_trace(raw, Settings())


def test_csv_retains_raw_samples_and_acquisition_metadata(tmp_path):
    raw = np.arange(SAMPLES, dtype=np.int32)
    frame = process_trace(raw, replace(Settings(), delay_us=100), simulated=True)
    path = tmp_path / "trace.csv"
    export_csv(path, frame)
    values = np.loadtxt(path, delimiter=",")
    np.testing.assert_array_equal(values[:, 2], raw)
    assert values[0, 0] == 100
    assert "source=simulation" in path.read_text(encoding="utf-8")
