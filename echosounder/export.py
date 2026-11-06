from pathlib import Path

import numpy as np

from .model import SAMPLE_RATE, Frame


def export_csv(path: str | Path, frame: Frame):
    source = "simulation" if frame.simulated else frame.settings.port
    header = (f"Echosounder Python; UTC={frame.acquired_at.isoformat()}; source={source}\n"
              f"sample_rate_hz={SAMPLE_RATE}; repetitions={frame.settings.repetitions}; "
              f"gain_code=0x{frame.settings.gain:02x}; sound_speed_m_s={frame.settings.sound_speed}\n"
              "time_us,depth_cm,raw_adc,signal_v,envelope_v")
    np.savetxt(path, np.column_stack((frame.time_us, frame.depth_cm, frame.raw,
                                    frame.voltage, frame.envelope)), delimiter=",",
               header=header, fmt=("%.9g", "%.9g", "%d", "%.12g", "%.12g"), encoding="utf-8")
