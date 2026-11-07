"""Dye signature matrix estimated from the data itself."""
from __future__ import annotations
import numpy as np
from scipy.cluster.vq import kmeans2

BASES = ("A", "C", "T", "G")


def mixing_angles(V: np.ndarray):
    """Return (A/C angle, T/G angle, red-pair fraction) in degrees / unitless for (N, 4) counts."""
    V = np.asarray(V, dtype=float)
    ta = np.degrees(np.arctan2(V[:, 1], V[:, 0]))   # 0 = pure A, 90 = pure C
    tg = np.degrees(np.arctan2(V[:, 3], V[:, 2]))   # 0 = pure T, 90 = pure G
    rf = (V[:, 0] + V[:, 1]) / V.sum(1)
    return ta, tg, rf


def _split_two(angle: np.ndarray, trim: float = 0.15, seed: int = 0):
    """Split a 1-D angle distribution into low/high groups by 2-means, then drop the `trim` fraction of each
    group that faces the boundary (the low group's top, the high group's bottom). Returns two boolean masks."""
    x = angle.reshape(-1, 1).astype(float)
    init = np.array([[np.percentile(angle, 25)], [np.percentile(angle, 75)]])
    cent, lab = kmeans2(x, init, minit="matrix", seed=seed)
    lo, hi = (0, 1) if cent[0, 0] <= cent[1, 0] else (1, 0)
    m_lo = lab == lo
    m_hi = lab == hi
    if m_lo.any():
        m_lo = m_lo & (angle <= np.percentile(angle[m_lo], 100 * (1 - trim)))
    if m_hi.any():
        m_hi = m_hi & (angle >= np.percentile(angle[m_hi], 100 * trim))
    return m_lo, m_hi


def seed_groups(V: np.ndarray, red_hi: float = 0.6, red_lo: float = 0.4, trim: float = 0.15) -> np.ndarray:
    """Label blocks 0..3 (A, C, T, G) that are confidently one base, -1 otherwise.

    Pair membership by red-pair fraction; within-pair split by 2-means on the mixing angle,
    dropping the `trim` fraction of each group nearest the boundary so seeds stay pure.
    """
    ta, tg, rf = mixing_angles(V)
    grp = np.full(len(V), -1)
    red = np.nonzero(rf > red_hi)[0]
    grn = np.nonzero(rf < red_lo)[0]
    if len(red) >= 4:
        a, c = _split_two(ta[red], trim)
        grp[red[a]] = 0
        grp[red[c]] = 1
    if len(grn) >= 4:
        t, g = _split_two(tg[grn], trim)
        grp[grn[t]] = 2
        grp[grn[g]] = 3
    return grp


def signature_matrix(V: np.ndarray, grp: np.ndarray) -> np.ndarray:
    """(4, 4) rows = base A, C, T, G; cols = channel A, C, T, G; each row scaled to max 1."""
    V = np.asarray(V, dtype=float)
    M = np.zeros((4, 4))
    for k in range(4):
        m = grp == k
        if m.sum() == 0:
            raise ValueError(f"no seed blocks for base {BASES[k]}")
        M[k] = np.median(V[m] / V[m].sum(1, keepdims=True), 0)
    return M / M.max(1, keepdims=True)


def contrast_ratios(M: np.ndarray) -> dict[str, float]:
    """Exposure-independent within-pair contrast: ratio of the two dyes' channel ratios."""
    ac = (M[1, 1] / M[1, 0]) / (M[0, 1] / M[0, 0])
    tg = (M[3, 3] / M[3, 2]) / (M[2, 3] / M[2, 2])
    return {"AC": float(ac), "TG": float(tg)}


def signature_angles(M: np.ndarray) -> dict[str, float]:
    def ang(u, v):
        return float(np.degrees(np.arccos(np.clip(np.dot(u, v) / np.linalg.norm(u) / np.linalg.norm(v), -1, 1))))
    return {"AC": ang(M[0], M[1]), "TG": ang(M[2], M[3]), "AT": ang(M[0], M[2]), "CG": ang(M[1], M[3])}
