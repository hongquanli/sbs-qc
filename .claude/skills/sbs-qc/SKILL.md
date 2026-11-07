---
name: sbs-qc
description: Use when asked to run, check, or interpret base-separability QC on sequencing-by-synthesis (SBS) in situ images (OME-TIFF fields from one sequencing cycle), to compare cycles, or to explain chastity, no-call, crosstalk matrix, or contrast-ratio numbers from sbs-qc output (stats.json, report.html).
---

# sbs-qc

The CLI is the instrument; the agent is the operator. Every number comes from
`sbs-qc analyze` at fixed settings. The agent runs it, reads `stats.json`,
answers the question, and does follow-up analysis with the library. It does not
re-derive the method and does not tune the settings.

## Run

```bash
sbs-qc analyze <fields>.ome.tiff --out <run>/qc/cycleNN/ --title "<run> cycle NN" [--notes notes.txt]
```

- One output directory per cycle, next to the data. Pass every field of the
  cycle in one call: the signature matrix is pooled across them.
- `sbs-qc --help` fails: the package is not installed in this environment. Say
  so and ask before installing (`pip install -e <repo>`).
- Channel mapping error, or a mapping that looks wrong: the OME channel names
  lack the base letters. Confirm from the acquisition config which emission
  band is T and which is G, then pass `--channels A,C,T,G,DAPI` in stored
  order. Do not guess the T/G assignment.
- Rebuild the page after editing notes: `sbs-qc report <dir> --notes notes.txt`.

## Read stats.json

| key | meaning |
|---|---|
| `contrast.AC`, `contrast.TG` | within-pair contrast ratio, exposure-independent; ≥ 3 comfortable, 2–3 limited, < 2 flagged |
| `matrix.values` | rows base A C T G, cols channel A C T G, row max 1; off-diagonal = crosstalk |
| `fields.<label>.pass_frac["0.6"]` | fraction of blocks at or above the chastity cut |
| `fields.<label>.no_call_frac` | 1 − pass; flagged above 0.20 |
| `fields.<label>.per_base.<B>.pass_frac` | the weak base shows here first |
| `fields.<label>.saturated_px` | per channel A C T G; > 100 flagged; fix = lower that channel's exposure or power |
| `fields.<label>.shifts_px` | per channel (dy, dx) vs A, px; > 1 flagged |
| `signature_angles_deg` | depend on exposure balance; not a separability measure |
| `params` | settings used; must match across cycles being compared |

Cross-pair leak (signal in the other laser pair over the own pair, from matrix
rows) above 35% is flagged: autofluorescence or dye carried over from the
previous cycle. Rising cycle over cycle means incomplete cleavage.

Verdict, same rule as the report: both contrasts ≥ 2 and every per-base pass
≥ 0.70 is separable; ≥ 1.3 and ≥ 0.50 is limited margin; otherwise not reliable.

## Frozen settings

`--block --sigma --fg-thresh --min-fg --chastity --trim --red-hi --red-lo` stay
at defaults. A cycle is comparable to the previous cycle only at the same
settings, and the matrix moves at the 0.05 level with `--trim` alone.

Change a setting only when the person asks for it. Then re-run every cycle of
the run at the new setting and say so in the answer. Not: "no-call looks high,
let me try `--trim 0.3`". Not: "the foreground threshold is clearly wrong for
this exposure". Report the number; the person decides.

Two settings follow the data, not the results. A camera that is not 12-bit
shifted into 16-bit (`channel_stats.max` far from 65520) needs `--ceiling`. A
pixel size other than 0.752 µm (`fields.<label>.pixel_um`) needs `--block`
scaled to keep about 6 µm. State the change in the answer.

## Answer shape

1. The verdict in one sentence, with the number that drove it: the weak pair's
   contrast, the worst per-base pass, or the flagged check.
2. What changed since the previous cycle, when one exists: matrix or pass-rate
   deltas.
3. The path to `report.html`. The report is the record; the chat answer is
   commentary.

## Follow-ups that are fair game

Anything that reads outputs or loaded stacks without changing the method:

```python
from sbs_qc import load_ome
from sbs_qc.pipeline import analyze
an = analyze([load_ome(p) for p in paths])      # same defaults as the CLI
fr = an.fields[0]
fr.call, fr.chas                                 # per kept block: call 0-3 = A C T G, chastity
yx = fr.feats.yx * fr.feats.block                # block origins in px, same order as fr.call
sel = (fr.call == 3) & (fr.chas < 0.6)           # e.g. low-chastity G blocks
y0, x0 = (yx[sel][0] - 100).clip(0)             # 200 px window, kept inside the image
crop = fr.feats.sm[:, y0:y0 + 200, x0:x0 + 200]  # four channels, one colony, one scale
```

Per-colony calls, matrix deltas between two `stats.json`, a named region in all
channels, a chastity histogram for one base, the exposure question (does the T
dye read stronger in the G band from band placement or exposure time). Each is
a few lines: write it, run it, report it.

## Common mistakes

- Reading `signature_angles_deg` as separability. Use `contrast`.
- Comparing cycles run at different `params`.
- Treating pass rates as absolute. The matrix is estimated from the data it
  scores, so they are an upper bound.
- Answering clipping with a reinterpretation instead of "lower the G exposure".
- Assuming which 545 nm band is T. Confirm against the acquisition config.
