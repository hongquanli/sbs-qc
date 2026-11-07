"""Background, smoothing, foreground and block-level features."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.ndimage import gaussian_filter


@dataclass
class BlockFeatures:
    V: np.ndarray          # (N, 4) mean background-subtracted counts per block, order A, C, T, G
    ok: np.ndarray         # (h, w) bool, which blocks are kept
    block: int             # block edge in px
    fg: np.ndarray         # (Y, X) bool foreground mask
    sm: np.ndarray         # (4, Y, X) smoothed, background-subtracted
    bg: np.ndarray         # (4,) background per channel
    sat_px: np.ndarray     # (4,) saturated pixel count per channel

    @property
    def yx(self) -> np.ndarray:
        """(N, 2) block row/col indices in the same order as V."""
        return np.argwhere(self.ok)

    def block_map(self, values: np.ndarray, fill=np.nan) -> np.ndarray:
        """Scatter per-block values back onto the (h, w) grid."""
        out = np.full(self.ok.shape, fill, dtype=np.asarray(values).dtype if np.isfinite(fill) else float)
        out[self.ok] = values
        return out


def channel_stats(base: np.ndarray, ceiling: int = 65520) -> dict:
    """Percentiles and saturation per channel (base is (C, Y, X))."""
    flat = base.reshape(base.shape[0], -1)
    pct = np.percentile(flat, [1, 50, 99, 99.9, 100], axis=1)
    return {
        "p1": pct[0].round(0).tolist(), "median": pct[1].round(0).tolist(), "p99": pct[2].round(0).tolist(),
        "p99_9": pct[3].round(0).tolist(), "max": pct[4].round(0).tolist(),
        "saturated_px": (flat >= ceiling).sum(1).tolist(),
    }


def block_features(base: np.ndarray, block: int = 8, sigma: float = 1.0, fg_thresh: float = 2500.0,
                   min_fg: float = 0.6, ceiling: int = 65520, bg_percentile: float = 1.0) -> BlockFeatures:
    """Per-block mean of smoothed, background-subtracted base channels over foreground pixels.

    base: (4, Y, X) in order A, C, T, G. Saturated pixels (any channel >= ceiling) are excluded.
    """
    base = np.asarray(base, dtype=np.float32)
    bg = np.percentile(base.reshape(4, -1), bg_percentile, axis=1)
    sm = np.stack([gaussian_filter(base[c] - bg[c], sigma) for c in range(4)])
    sat = base >= ceiling
    fg = (sm.max(0) > fg_thresh) & ~sat.any(0)
    H, W = fg.shape
    h, w = H // block, W // block
    fgc = fg[: h * block, : w * block].reshape(h, block, w, block)
    fgb = fgc.mean((1, 3))
    smc = sm[:, : h * block, : w * block] * fg[None, : h * block, : w * block]
    V = smc.reshape(4, h, block, w, block).sum((2, 4)) / np.maximum(fgb * block * block, 1)
    ok = fgb >= min_fg
    Vb = np.clip(V[:, ok].T, 1, None)
    return BlockFeatures(V=Vb, ok=ok, block=block, fg=fg, sm=sm, bg=bg, sat_px=sat.sum((1, 2)))
