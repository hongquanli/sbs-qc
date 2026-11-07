"""Chromatic / mechanical shift between channels."""
from __future__ import annotations
import numpy as np
from skimage.registration import phase_cross_correlation
from skimage.transform import downscale_local_mean


def channel_shifts(data: np.ndarray, ref: int = 0, downsample: int = 2, upsample: int = 10) -> list[tuple[float, float]]:
    """(dy, dx) in full-resolution pixels of every channel relative to `ref`, by phase correlation."""
    d = max(1, int(downsample))
    r = downscale_local_mean(np.asarray(data[ref], dtype=np.float32), (d, d))
    out = []
    for c in range(data.shape[0]):
        mv = downscale_local_mean(np.asarray(data[c], dtype=np.float32), (d, d))
        sh, _, _ = phase_cross_correlation(r, mv, upsample_factor=upsample)
        out.append((float(sh[0] * d), float(sh[1] * d)))
    return out
