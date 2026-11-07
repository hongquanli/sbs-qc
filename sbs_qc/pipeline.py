"""End-to-end analysis of one or more fields."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
import numpy as np
from .io import Stack
from .features import BlockFeatures, block_features, channel_stats
from .signatures import mixing_angles, seed_groups, signature_matrix, contrast_ratios, signature_angles
from .unmix import unmix, chastity, call_bases
from .registration import channel_shifts

BASES = ("A", "C", "T", "G")


@dataclass
class Params:
    block: int = 8            # block edge, px
    sigma: float = 1.0        # Gaussian smoothing, px
    fg_thresh: float = 2500.0 # foreground: max base channel above background, counts
    min_fg: float = 0.6       # block kept if this fraction of its pixels is foreground
    ceiling: int = 65520      # saturation value (12-bit shifted into 16-bit)
    chastity_cut: float = 0.6 # Illumina pass threshold
    red_hi: float = 0.6       # red-pair fraction above which a block seeds A or C
    red_lo: float = 0.4       # ... below which it seeds T or G
    trim: float = 0.15        # fraction of each seed group nearest the within-pair boundary dropped
    registration: bool = True


@dataclass
class FieldResult:
    label: str
    stack: Stack
    feats: BlockFeatures
    W: np.ndarray
    chas: np.ndarray
    call: np.ndarray
    ta: np.ndarray
    tg: np.ndarray
    rf: np.ndarray
    shifts: list | None = None
    stats: dict = field(default_factory=dict)


@dataclass
class Analysis:
    M: np.ndarray
    fields: list[FieldResult]
    params: Params
    stats: dict


def analyze(stacks: list[Stack], params: Params | None = None, labels: list[str] | None = None) -> Analysis:
    p = params or Params()
    labels = labels or [s.path.split("/")[-1].split(".")[0] or f"field{i}" for i, s in enumerate(stacks)]
    feats = [block_features(s.base, p.block, p.sigma, p.fg_thresh, p.min_fg, p.ceiling) for s in stacks]
    Vp = np.concatenate([f.V for f in feats])
    grp = seed_groups(Vp, p.red_hi, p.red_lo, p.trim)
    M = signature_matrix(Vp, grp)
    stats = {
        "params": asdict(p),
        "matrix": {"rows": list(BASES), "cols": list(BASES), "values": M.round(3).tolist()},
        "seed_counts": [int((grp == k).sum()) for k in range(4)],
        "contrast": contrast_ratios(M),
        "signature_angles_deg": signature_angles(M),
        "fields": {},
    }
    fields = []
    for s, f, lab in zip(stacks, feats, labels):
        W = unmix(f.V, M)
        ch = chastity(W)
        call = call_bases(W)
        ta, tg, rf = mixing_angles(f.V)
        shifts = channel_shifts(s.data) if p.registration else None
        fs = {
            "n_blocks": int(len(f.V)), "fg_px": int(f.fg.sum()), "fg_frac": float(f.fg.mean()),
            "background": f.bg.round(0).tolist(), "saturated_px": f.sat_px.tolist(),
            "channel_stats": channel_stats(s.base, p.ceiling),
            "call_frac": [float(np.mean(call == k)) for k in range(4)],
            "chastity_median": float(np.median(ch)),
            "pass_frac": {str(c): float(np.mean(ch >= c)) for c in (0.6, 0.7, 0.8)},
            "no_call_frac": float(np.mean(ch < p.chastity_cut)),
            "per_base": {BASES[k]: {"n": int((call == k).sum()),
                                    "chastity_median": float(np.median(ch[call == k])) if (call == k).any() else None,
                                    "pass_frac": float(np.mean(ch[call == k] >= p.chastity_cut)) if (call == k).any() else None}
                         for k in range(4)},
            "shifts_px": shifts, "channel_names": s.names, "pixel_um": s.pixel_um,
        }
        stats["fields"][lab] = fs
        fields.append(FieldResult(lab, s, f, W, ch, call, ta, tg, rf, shifts, fs))
    return Analysis(M=M, fields=fields, params=p, stats=stats)
