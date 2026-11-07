"""Command line: sbs-qc analyze FIELD.ome.tiff [...] --out DIR"""
from __future__ import annotations
import argparse, json, os, sys
import numpy as np
from .io import load_ome
from .pipeline import Params, analyze

BASES = ("A", "C", "T", "G")


def _summary(an) -> str:
    M = an.M; c = an.stats["contrast"]
    lines = ["Dye signature matrix (rows = base, cols = channel A C T G; row max = 1):"]
    for k in range(4):
        lines.append(f"  {BASES[k]}:  " + "  ".join(f"{M[k, j]:.2f}" for j in range(4)))
    lines.append(f"Contrast ratio  A/C {c['AC']:.2f}x   T/G {c['TG']:.2f}x")
    lines.append(f"{'field':<14}{'blocks':>8}{'A':>6}{'C':>6}{'T':>6}{'G':>6}{'chas med':>10}{'pass':>7}{'no call':>9}{'sat G px':>10}")
    for lab, fs in an.stats["fields"].items():
        cf = fs["call_frac"]
        lines.append(f"{lab:<14}{fs['n_blocks']:>8,}" + "".join(f"{x * 100:>5.0f}%" for x in cf)
                     + f"{fs['chastity_median']:>10.2f}{fs['pass_frac'][str(an.params.chastity_cut)] * 100:>6.0f}%{fs['no_call_frac'] * 100:>8.0f}%{fs['saturated_px'][3]:>10,}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sbs-qc", description="Base-separability QC for SBS in situ images")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="signature matrix, unmixing, chastity, figures")
    a.add_argument("files", nargs="+", help="OME-TIFF fields (C, Y, X)")
    a.add_argument("--out", required=True, help="output directory")
    a.add_argument("--channels", help="override channel names, e.g. A,C,T,G,DAPI (order as stored)")
    a.add_argument("--labels", help="comma-separated field labels (default: file stems)")
    a.add_argument("--block", type=int, default=8)
    a.add_argument("--sigma", type=float, default=1.0)
    a.add_argument("--fg-thresh", type=float, default=2500.0)
    a.add_argument("--min-fg", type=float, default=0.6)
    a.add_argument("--ceiling", type=int, default=65520)
    a.add_argument("--chastity", type=float, default=0.6)
    a.add_argument("--trim", type=float, default=None, help="fraction of each seed group nearest the within-pair boundary dropped (default 0.15)")
    a.add_argument("--red-hi", type=float, default=None, help="red-pair fraction above which a block can seed A or C")
    a.add_argument("--red-lo", type=float, default=None, help="red-pair fraction below which a block can seed T or G")
    a.add_argument("--no-registration", action="store_true")
    a.add_argument("--no-figures", action="store_true")
    a.add_argument("--themes", default="light,dark")
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    stacks = [load_ome(f, args.channels) for f in args.files]
    labels = args.labels.split(",") if args.labels else None
    p = Params(block=args.block, sigma=args.sigma, fg_thresh=args.fg_thresh, min_fg=args.min_fg, ceiling=args.ceiling,
               chastity_cut=args.chastity, registration=not args.no_registration)
    for name in ("trim", "red_hi", "red_lo"):
        if getattr(args, name) is not None:
            setattr(p, name, getattr(args, name))
    an = analyze(stacks, p, labels)
    with open(os.path.join(args.out, "stats.json"), "w") as fh:
        json.dump(an.stats, fh, indent=1)
    np.savetxt(os.path.join(args.out, "matrix.csv"), an.M, delimiter=",", fmt="%.4f", header="cols A,C,T,G; rows A,C,T,G", comments="# ")
    if not args.no_figures:
        from .figures import all_figures
        all_figures(an, args.out, tuple(t.strip() for t in args.themes.split(",") if t.strip()))
    print(_summary(an))
    print(f"\nwrote {args.out}/stats.json, matrix.csv" + ("" if args.no_figures else ", figures"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
