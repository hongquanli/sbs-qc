import numpy as np
from sbs_qc.registration import channel_shifts
from synth import make_field


def test_detects_integer_shift():
    stack, _ = make_field(seed=5, size=256, n_col=8)
    data = stack.data[:4].copy()
    data[2] = np.roll(np.roll(data[0], 3, axis=0), -2, axis=1)   # T = A moved +3 rows, -2 cols
    sh = channel_shifts(data, ref=0, downsample=1)
    assert sh[0] == (0.0, 0.0)
    dy, dx = sh[2]
    assert abs(abs(dy) - 3) < 0.3 and abs(abs(dx) - 2) < 0.3
    assert np.sign(dy) == -np.sign(dx)  # opposite signs, whichever convention
