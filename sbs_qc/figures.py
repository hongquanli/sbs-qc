"""Figures. Base colours are a CVD-validated set (dataviz validator, all pairs, with letter labels as the
secondary encoding): warm for the A/C pair, cool for the T/G pair. Charts render per theme on a transparent
background; image panels sit on black and use the dark steps."""
from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import to_rgb
from scipy.ndimage import label, center_of_mass
from .pipeline import Analysis, FieldResult

BASES = ("A", "C", "T", "G")
PALETTE = {
    "light": {"A": "#e34948", "C": "#eda100", "T": "#1baf7a", "G": "#2a78d6", "ink": "#0b0b0b", "ink2": "#52514e",
              "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7"},
    "dark": {"A": "#dc3c3c", "C": "#c98500", "T": "#199e70", "G": "#3987e5", "ink": "#f0efec", "ink2": "#c3c2b7",
             "muted": "#898781", "grid": "#2c2c2a", "axis": "#383835"},
}
IMG = PALETTE["dark"]


def style(theme: str, grid: bool = True) -> dict:
    p = PALETTE[theme]
    plt.rcParams.update({
        "text.color": p["ink2"], "axes.labelcolor": p["ink2"], "axes.edgecolor": p["axis"], "xtick.color": p["muted"],
        "ytick.color": p["muted"], "axes.titlecolor": p["ink"], "grid.color": p["grid"], "grid.linewidth": 0.6,
        "axes.grid": grid, "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
        "font.size": 11, "axes.titlesize": 12, "legend.frameon": False, "figure.facecolor": "none",
        "axes.facecolor": "none", "savefig.facecolor": "none", "savefig.transparent": True})
    return p


def _region(ok: np.ndarray, mask_blocks: np.ndarray, block: int, minsize: int, maxsize: int):
    m = np.zeros(ok.shape, bool)
    m[ok] = mask_blocks
    lab, n = label(m)
    if n == 0:
        return None
    sizes = np.bincount(lab.ravel())[1:]
    cands = [(s, k + 1) for k, s in enumerate(sizes) if minsize <= s <= maxsize] or [(s, k + 1) for k, s in enumerate(sizes)]
    s, k = max(cands)
    cy, cx = center_of_mass(lab == k)
    return int(cy * block), int(cx * block), int(s)


def _crop(arr: np.ndarray, cy: int, cx: int, S: int):
    H, W = arr.shape[-2:]
    S = min(S, H, W)
    y0 = int(np.clip(cy - S // 2, 0, H - S)); x0 = int(np.clip(cx - S // 2, 0, W - S))
    return arr[..., y0:y0 + S, x0:x0 + S], (y0, x0)


def composite(sm4: np.ndarray, vmax: float, pal: dict = IMG) -> np.ndarray:
    out = np.zeros(sm4.shape[1:] + (3,), np.float32)
    for k in range(4):
        out += np.clip(sm4[k] / vmax, 0, 1)[..., None] * np.array(to_rgb(pal[BASES[k]]))
    return np.clip(out, 0, 1)


def _blank(ax, title=None, color=None):
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    if title:
        ax.set_title(title, color=color or PALETTE["light"]["muted"])


def fig_colonies(fr: FieldResult, out: str, S: int = 200, chastity_min: float = 0.85, minsize: int = 40, maxsize: int = 350) -> str:
    """One colony per called base, the four channels on a shared scale, plus a composite."""
    style("dark", grid=False)
    fig, axs = plt.subplots(4, 5, figsize=(15, 12.4))
    for k in range(4):
        reg = _region(fr.feats.ok, (fr.call == k) & (fr.chas > chastity_min), fr.feats.block, minsize, maxsize)
        if reg is None:
            for c in range(5):
                _blank(axs[k, c])
            axs[k, 0].text(0.5, 0.5, f"no colony called {BASES[k]}", transform=axs[k, 0].transAxes, ha="center", color=IMG["ink2"])
            continue
        cy, cx, _ = reg
        sm4, (y0, x0) = _crop(fr.feats.sm, cy, cx, S)
        vmax = float(max(np.percentile(sm4[c], 99.7) for c in range(4))) or 1.0
        for c in range(4):
            axs[k, c].imshow(sm4[c], cmap="gray", vmin=0, vmax=vmax, interpolation="nearest")
            _blank(axs[k, c], f"{BASES[c]} channel" if k == 0 else None)
            if c == 0:
                axs[k, c].set_ylabel(f"called {BASES[k]}", color=IMG[BASES[k]], fontsize=13, fontweight="bold")
        axs[k, 4].imshow(composite(sm4, vmax), interpolation="nearest")
        _blank(axs[k, 4], "composite" if k == 0 else None)
        axs[k, 0].text(4, sm4.shape[-1] - 6, f"{fr.label}  y{y0} x{x0}  max {vmax:.0f} cts", color="#c3c2b7", fontsize=8, va="bottom")
    plt.subplots_adjust(wspace=0.03, hspace=0.06, left=0.03, right=0.99, top=0.96, bottom=0.01)
    path = f"{out}/colonies_{fr.label}.png"
    plt.savefig(path, dpi=90); plt.close()
    return path


def fig_nocall(fr: FieldResult, out: str, cut: float = 0.6, S: int = 260) -> str | None:
    """Largest connected low-chastity region: the four channels on one scale, DAPI if present, composite."""
    reg = _region(fr.feats.ok, fr.chas < cut, fr.feats.block, 10, 10 ** 9)
    if reg is None:
        return None
    cy, cx, n = reg
    style("dark", grid=False)
    dapi = fr.stack.dapi
    ncol = 6 if dapi is not None else 5
    fig, axs = plt.subplots(1, ncol, figsize=(3 * ncol, 3.4))
    sm4, (y0, x0) = _crop(fr.feats.sm, cy, cx, S)
    vmax = float(max(np.percentile(sm4[c], 99.7) for c in range(4))) or 1.0
    for c in range(4):
        axs[c].imshow(sm4[c], cmap="gray", vmin=0, vmax=vmax, interpolation="nearest"); _blank(axs[c], f"{BASES[c]} channel")
    i = 4
    if dapi is not None:
        d, _ = _crop(dapi - np.percentile(dapi, 1), cy, cx, S)
        axs[i].imshow(d, cmap="gray", vmin=0, vmax=np.percentile(d, 99.7) or 1, interpolation="nearest"); _blank(axs[i], "DAPI"); i += 1
    axs[i].imshow(composite(sm4, vmax), interpolation="nearest"); _blank(axs[i], "composite")
    axs[0].text(4, sm4.shape[-1] - 6, f"{fr.label}  y{y0} x{x0}  {n} low-chastity blocks", color="#c3c2b7", fontsize=8, va="bottom")
    plt.subplots_adjust(wspace=0.03, left=0.01, right=0.99, top=0.9, bottom=0.01)
    path = f"{out}/nocall_{fr.label}.png"
    plt.savefig(path, dpi=90); plt.close()
    return path


def save_callmap(fr: FieldResult, out: str, cut: float = 0.6, scale: int = 4) -> tuple[str, str]:
    """Block call map (dimmed below the chastity cut) and a half-resolution composite in the same colours."""
    ok = fr.feats.ok
    cm = np.zeros(ok.shape + (3,), np.float32)
    cols = np.array([to_rgb(IMG[b]) for b in BASES])
    cm[ok] = cols[fr.call] * np.where(fr.chas >= cut, 1.0, 0.35)[:, None]
    p1 = f"{out}/callmap_{fr.label}.png"
    plt.imsave(p1, np.kron(cm, np.ones((scale, scale, 1))).clip(0, 1))
    sm2 = fr.feats.sm[:, ::2, ::2]
    vmax = float(max(np.percentile(sm2[c], 99.7) for c in range(4))) or 1.0
    p2 = f"{out}/composite_{fr.label}.png"
    plt.imsave(p2, composite(sm2, vmax))
    return p1, p2


def fig_pairs(an: Analysis, out: str, theme: str = "light") -> str:
    """Within-pair mixing-angle histograms, coloured by called base."""
    p = style(theme)
    ta = np.concatenate([f.ta for f in an.fields]); tg = np.concatenate([f.tg for f in an.fields])
    rf = np.concatenate([f.rf for f in an.fields]); call = np.concatenate([f.call for f in an.fields])
    c = an.stats["contrast"]
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.6))
    m = rf > an.params.red_hi
    for k in (0, 1):
        axs[0].hist(ta[m & (call == k)], bins=120, range=(0, 90), color=p[BASES[k]], alpha=0.85, label=f"called {BASES[k]}")
    axs[0].set_xlabel("A/C angle = atan2(C, A) [°]  (red-pair blocks)"); axs[0].set_ylabel("blocks")
    axs[0].set_title(f"A vs C: contrast ratio {c['AC']:.1f}×"); axs[0].legend()
    m = rf < an.params.red_lo
    for k in (2, 3):
        axs[1].hist(tg[m & (call == k)], bins=120, range=(0, 90), color=p[BASES[k]], alpha=0.85, label=f"called {BASES[k]}")
    axs[1].set_xlabel("T/G angle = atan2(G, T) [°]  (green-pair blocks)")
    axs[1].set_title(f"T vs G: contrast ratio {c['TG']:.1f}×"); axs[1].legend()
    plt.tight_layout()
    path = f"{out}/pairs_{theme}.png"
    plt.savefig(path, dpi=90); plt.close()
    return path


def fig_scatter(an: Analysis, out: str, theme: str = "light") -> str:
    """A/C angle vs T/G angle per block, coloured by called base, faded below the chastity cut."""
    p = style(theme); M = an.M; cut = an.params.chastity_cut
    n = len(an.fields)
    fig, axs = plt.subplots(1, n, figsize=(5.3 * n + 0.5, 5.4), sharey=True, squeeze=False)
    axs = axs[0]
    for ax, fr in zip(axs, an.fields):
        lo = fr.chas < cut
        for k in range(4):
            m = (fr.call == k) & lo
            ax.scatter(fr.ta[m], fr.tg[m], c=p[BASES[k]], s=1.8, alpha=0.12, linewidths=0, rasterized=True)
        for k in range(4):
            m = (fr.call == k) & ~lo
            ax.scatter(fr.ta[m], fr.tg[m], c=p[BASES[k]], s=1.8, alpha=0.85, linewidths=0, rasterized=True)
        for k in range(4):
            x = np.degrees(np.arctan2(M[k, 1], M[k, 0])); y = np.degrees(np.arctan2(M[k, 3], M[k, 2]))
            ax.scatter([x], [y], s=300, facecolors="none", edgecolors=p["ink"], linewidths=1.6)
            ax.text(x, y, BASES[k], ha="center", va="center", fontsize=10, fontweight="bold", color=p["ink"])
        ax.set_title(f"{fr.label}  ·  {len(fr.chas):,} blocks  ·  {np.mean(lo) * 100:.0f}% no call")
        ax.set_xlabel("A/C angle = atan2(C, A) [°]")
    axs[0].set_ylabel("T/G angle = atan2(G, T) [°]")
    handles = [Line2D([], [], marker="o", ls="", ms=7, color=p[b], label=f"called {b}") for b in BASES]
    handles.append(Line2D([], [], marker="o", ls="", ms=7, color=p["muted"], alpha=0.3, label=f"faded: chastity < {cut} (no call)"))
    fig.legend(handles=handles, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.04))
    plt.tight_layout()
    path = f"{out}/scatter_{theme}.png"
    plt.savefig(path, dpi=90, bbox_inches="tight"); plt.close()
    return path


def fig_chastity(an: Analysis, out: str, theme: str = "light") -> str:
    p = style(theme); cut = an.params.chastity_cut
    ch = np.concatenate([f.chas for f in an.fields]); call = np.concatenate([f.call for f in an.fields])
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for k in range(4):
        ax.hist(ch[call == k], bins=60, range=(0.5, 1.0), histtype="step", linewidth=2, color=p[BASES[k]],
                label=f"called {BASES[k]}  (n={int((call == k).sum()):,})")
    ax.axvline(cut, color=p["ink2"], linewidth=1)
    ax.set_yscale("log")
    ax.text(cut + 0.003, ax.get_ylim()[1] * 0.95, f"pass ≥ {cut}", color=p["ink2"], va="top", fontsize=10)
    ax.set_xlabel("chastity = top weight / (top + second) after NNLS unmixing"); ax.set_ylabel("blocks")
    ax.set_title("Per-block chastity, all fields pooled"); ax.legend(loc="upper center")
    plt.tight_layout()
    path = f"{out}/chastity_{theme}.png"
    plt.savefig(path, dpi=90); plt.close()
    return path


def all_figures(an: Analysis, out: str, themes=("light", "dark")) -> list[str]:
    paths = []
    for th in themes:
        paths += [fig_pairs(an, out, th), fig_scatter(an, out, th), fig_chastity(an, out, th)]
    for fr in an.fields:
        paths.append(fig_colonies(fr, out))
        paths += list(save_callmap(fr, out, an.params.chastity_cut))
        nc = fig_nocall(fr, out, an.params.chastity_cut)
        if nc:
            paths.append(nc)
    return paths
