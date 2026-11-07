"""Synthetic SBS field: disc colonies of four bases with a known signature matrix."""
from __future__ import annotations
import numpy as np
from scipy.ndimage import gaussian_filter
from sbs_qc.io import Stack

M_TRUE = np.array([[1.00, 0.44, 0.09, 0.24],
                   [0.68, 1.00, 0.14, 0.32],
                   [0.26, 0.23, 0.46, 1.00],
                   [0.12, 0.09, 0.19, 1.00]])
NAMES = ["Fluorescence 638 nm Ex - A", "Fluorescence 638 nm Ex - C", "Fluorescence 545 nm Ex - T",
         "Fluorescence 545 nm Ex - G", "Fluorescence 405 nm Ex"]


def make_field(seed: int = 0, size: int = 640, n_col: int = 16, amp: float = 12000.0, bg: float = 800.0,
               read_noise: float = 40.0, M: np.ndarray = M_TRUE):
    rng = np.random.default_rng(seed)
    img = np.zeros((4, size, size), np.float64)
    truth = np.full((size, size), -1, np.int8)
    yy, xx = np.mgrid[:size, :size]
    placed = []
    for i in range(n_col):
        base = i % 4
        for _ in range(200):
            cy, cx = rng.integers(50, size - 50, 2); r = int(rng.integers(24, 42))
            if all((cy - py) ** 2 + (cx - px) ** 2 > (r + pr + 12) ** 2 for py, px, pr in placed):
                break
        placed.append((cy, cx, r))
        disc = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
        texture = 1 + 0.5 * gaussian_filter(rng.normal(size=(size, size)), 3) / 0.1
        a = amp * rng.uniform(0.6, 1.4)
        for c in range(4):
            img[c][disc] += a * M[base, c] * np.clip(texture[disc], 0.3, 2.0)
        truth[disc] = base
    for c in range(4):
        img[c] = gaussian_filter(img[c], 1.2)
        img[c] = bg + img[c] + rng.normal(0, read_noise, img[c].shape) + rng.normal(0, 1, img[c].shape) * np.sqrt(np.maximum(img[c], 0)) * 0.5
    dapi = bg + 3000 * (truth >= 0) + rng.normal(0, read_noise, (size, size))
    data = np.concatenate([img, dapi[None]])
    data = (np.clip(np.round(data / 16) * 16, 0, 65520)).astype(np.uint16)
    stack = Stack(data=data, names=NAMES, base_idx={"A": 0, "C": 1, "T": 2, "G": 3}, dapi_idx=4, pixel_um=0.752, path=f"synth{seed}.ome.tiff")
    return stack, truth


def block_truth(truth: np.ndarray, ok: np.ndarray, block: int) -> np.ndarray:
    """Per kept block: the base if every pixel agrees, else -1."""
    h, w = ok.shape
    t = truth[: h * block, : w * block].reshape(h, block, w, block)
    mx = t.max((1, 3)); mn = t.min((1, 3))
    uniform = np.where(mx == mn, mx, -1)
    return uniform[ok]
