"""Non-negative unmixing, chastity and base calls."""
from __future__ import annotations
import numpy as np
from scipy.optimize import nnls


def unmix(V: np.ndarray, M: np.ndarray) -> np.ndarray:
    """Per-block non-negative least squares: V[i] ~ M.T @ W[i]. Returns (N, 4) weights."""
    MT = np.asarray(M, dtype=float).T
    return np.array([nnls(MT, v)[0] for v in np.asarray(V, dtype=float)])


def chastity(W: np.ndarray) -> np.ndarray:
    """Illumina-style chastity: top weight / (top + second)."""
    s = np.sort(np.asarray(W, dtype=float), 1)[:, ::-1]
    return s[:, 0] / np.maximum(s[:, 0] + s[:, 1], 1e-9)


def call_bases(W: np.ndarray) -> np.ndarray:
    """Index 0..3 (A, C, T, G) of the largest weight."""
    return np.asarray(W).argmax(1)
