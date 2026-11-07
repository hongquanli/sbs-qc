# sbs-qc

Base-separability QC for sequencing-by-synthesis (SBS) in situ images.

Give it one or more multi-channel fields from one sequencing cycle and it answers:
can the four bases be told apart, what is the dye crosstalk matrix, how many
blocks pass an Illumina-style chastity filter, and where are the no-call regions.

Built from the 2026-11-06 analysis of three fields imaged 2026-11-03 on a Squid
with MiSeq reagents (638 nm excitation for A/C, 545 nm for T/G, DAPI at 405 nm).
Report for that run: https://claude.ai/artifact/AQTLuf3duQAfazcZ9rCSDJ

## Install

```bash
pip install -e .            # numpy, scipy, scikit-image, tifffile, matplotlib
pip install -e ".[test]"    # + pytest
```

## Run

```bash
sbs-qc analyze field_01.ome.tiff field_02.ome.tiff --out results/
```

Input: OME-TIFF, axes C,Y,X, one plane per channel. Base channels are found by a
trailing letter in the OME channel name (`Fluorescence 638 nm Ex - A`, `G`,
`ch_T`...). DAPI is recognised by name or by `405`. If the names do not carry
the letters, pass the order explicitly:

```bash
sbs-qc analyze f.ome.tiff --out results/ --channels A,C,T,G,DAPI
```

Options and defaults:

| flag | default | meaning |
|---|---|---|
| `--block` | 8 | block edge in px (8 px at 0.752 µm/px = 6 µm, about one cell) |
| `--sigma` | 1.0 | Gaussian smoothing before everything else, px |
| `--fg-thresh` | 2500 | foreground: max base channel above background, counts |
| `--min-fg` | 0.6 | a block is kept if this fraction of its pixels is foreground |
| `--ceiling` | 65520 | saturation value (12-bit camera shifted into 16 bits) |
| `--chastity` | 0.6 | pass threshold for calls |
| `--trim` | 0.15 | fraction of each seed group nearest the within-pair boundary dropped |
| `--red-hi`, `--red-lo` | 0.6, 0.4 | red-pair fraction limits for seeding A/C and T/G |
| `--labels` | file stems | field labels for figures and stats |
| `--themes` | light,dark | chart renders (image panels are theme-independent) |
| `--no-registration` | | skip the channel-shift check |
| `--no-figures` | | stats and matrix only (also skips the report) |
| `--no-report` | | figures but no `report.html` |
| `--title`, `--notes` | | report title; a text file of hand-written interpretation (paragraphs, `- ` bullets) |

## Report

`analyze` ends by writing `report.html`: a single self-contained page (figures
inlined as data URIs, light and dark themes) with the verdict, headline numbers,
automatic checks (within-pair contrast, saturation, registration, no-call rate,
cross-pair leak), your notes if given, every figure with captions, the signature
matrix, per-field and per-base tables, and the method with the parameters used.
Open it in a browser or send it as one file.

To rebuild the report from an existing output directory, or change its form:

```bash
sbs-qc report results/ --title "Cycle 3" --notes notes.txt
sbs-qc report results/ --link-figures     # reference the PNGs instead of inlining
sbs-qc report results/ --fragment         # body only, for embedding (e.g. a claude.ai artifact)
```

## Outputs

`report.html` — see above.

`stats.json` — everything numeric: the signature matrix, contrast ratios, angles
between signatures, and per field: block count, foreground fraction, saturated
pixels and intensity percentiles per channel, call fractions, chastity median
and pass fractions at 0.6 / 0.7 / 0.8, per-base pass rates, no-call fraction,
channel shifts in px.

`matrix.csv` — the 4 × 4 signature matrix, rows = base A C T G, columns = channel
A C T G, each row scaled to its brightest channel.

Figures:

| file | what it shows |
|---|---|
| `colonies_<field>.png` | one high-chastity colony per called base, the four channels on one intensity scale, plus a composite |
| `pairs_<theme>.png` | A/C mixing angle for red-pair blocks and T/G angle for green-pair blocks, coloured by call |
| `scatter_<theme>.png` | every block, A/C angle vs T/G angle, coloured by call, faded below the chastity cut |
| `chastity_<theme>.png` | chastity distribution per called base, log scale, with the cut |
| `callmap_<field>.png` | block call map, dimmed below the cut (4× block scale) |
| `composite_<field>.png` | half-resolution four-colour composite of the raw channels |
| `nocall_<field>.png` | the largest connected low-chastity region, all channels on one scale |

## Method

1. **Background**: per-channel 1st percentile, subtracted.
2. **Smoothing**: Gaussian, σ = 1 px.
3. **Foreground**: maximum of the four base channels above `fg_thresh`, excluding
   any pixel saturated in any channel.
4. **Blocks**: `block` × `block` px with at least `min_fg` foreground; feature =
   mean of foreground pixels per channel. Signal in these samples was colony-level
   cytoplasmic fill, not single rolling-circle puncta, so blocks are the unit.
5. **Seeds**: red-pair fraction (A+C)/(A+C+T+G) above `red_hi` (0.6) or below
   `red_lo` (0.4) picks the pair; a 2-means split on the within-pair mixing angle
   picks the base; the `trim` fraction (0.15) of each group nearest the boundary
   is dropped so mixed blocks do not pull the seed.
6. **Signature matrix**: median normalised 4-vector of each seed group, pooled over
   all fields, rows scaled to max 1. The matrix moves at the 0.05 level with the
   seed rule (`--trim 0` to `--trim 0.5` spans A/C contrast 3.3× to 4.7× on the
   2026-11-03 fields), so compare runs at the same settings.
7. **Calls**: non-negative least squares against the matrix; call = largest weight;
   chastity = top / (top + second).
8. **Registration check**: phase cross-correlation of every channel against A on
   2× downsampled fields.

Two numbers summarise separability. The **contrast ratio** of a pair is how much
the within-pair channel ratio differs between the two dyes (for A/C:
(C/A of the C dye) / (C/A of the A dye)). It is independent of exposure balance.
**Chastity** is also independent of exposure balance, because a 4 × 4 unmix is
exact whenever all weights are positive. Angles between signature vectors are
reported but depend on how exposures were balanced.

Caveats: the matrix is estimated from the same data it scores, so pass rates are
an upper bound. No phasing or pre-phasing correction applies within one cycle.
Blocks that straddle two colonies, colony edges, and heterogeneous colonies land
in the no-call zone by design.

## Reading the scatter

Read `scatter_*.png` as a plus sign. For A and C blocks only the horizontal
position carries information (A left, C right). For T and G blocks only the
vertical position does (G top, T bottom). The faint cloud at the crossing is the
no-call zone. Parallel streaks within one colour are individual colonies, each
with its own leak ratio; calling per colony would be tighter than per block.

## Library use

```python
from sbs_qc import load_ome
from sbs_qc.pipeline import Params, analyze
from sbs_qc.figures import all_figures

stacks = [load_ome(p) for p in paths]
an = analyze(stacks, Params(block=8, chastity_cut=0.6))
an.M                      # 4x4 signature matrix
an.stats["contrast"]      # {'AC': ..., 'TG': ...}
fr = an.fields[0]         # fr.call, fr.chas, fr.feats.V, fr.feats.ok, fr.W
all_figures(an, "results/")
```

## Results from the 2026-11-03 fields

Tool output at default settings (`sbs-qc analyze manual_64 manual_65 manual_66`).
Signature matrix, rows = base, columns = channel:

| | A | C | T | G |
|---|---|---|---|---|
| A | 1.00 | 0.42 | 0.09 | 0.23 |
| C | 0.65 | 1.00 | 0.13 | 0.30 |
| T | 0.26 | 0.25 | 0.51 | 1.00 |
| G | 0.14 | 0.11 | 0.21 | 1.00 |

Contrast ratios: A/C 3.6×, T/G 2.4×. Chastity ≥ 0.6: 89%, 87% and 96% of blocks
in the three fields; per base A 87–98%, C 87–98%, T 81–92%, G 88–97%. No-call
fraction 11%, 13% and 4%. Channel shifts under 1 px. The G channel clipped about
3,100 pixels per dense field. The T dye read 2× stronger through the G band
(578/21) than through the T band (624/40); whether that is exposure balance or
band placement needs the per-channel exposure times.

The report page linked above was made with hand-set seed thresholds instead of
the 2-means split; it shows A/C 3.3× and T/G 2.5×, and the intermediate colony in
field 66 as no-call rather than low-chastity G. Both are within the seed
sensitivity noted under Method.

`examples/2026-11-03/` holds `stats.json` and `matrix.csv` from the default run.

## Colours

Base colours are a colour-vision-deficiency-validated set (worst all-pairs ΔE
above the floor with the letter labels as secondary encoding): A red, C yellow,
T aqua, G blue. Warm for the 638 nm pair, cool for the 545 nm pair. Light and
dark steps live in `sbs_qc/figures.py`.

## Tests

```bash
PYTHONPATH=. pytest
```

Synthetic fields with disc colonies of known signature matrix check matrix
recovery (within 0.08), call accuracy (above 97% on uniform blocks), pass rate,
OME channel mapping, registration, the CLI end to end, and the report (structure,
inlined figures, notes, fragment and linked-figure modes).
