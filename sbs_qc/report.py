"""Self-contained HTML report from an output directory (stats.json + figures)."""
from __future__ import annotations
import base64, datetime as _dt, html, json, os

BASES = ("A", "C", "T", "G")
CSS = """
:root{--bg:#f5f6f7;--surface:#fff;--fg:#15181a;--fg2:#4a5056;--muted:#7d858b;--line:#dcdfe2;--line-strong:#b9bfc4;
--A:#e34948;--C:#eda100;--T:#1baf7a;--G:#2a78d6;--warn:#b35c00;--ok:#1f7a3f;--img-bg:#000;--show-light:block;--show-dark:none;
--sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;--mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#121415;--surface:#1a1d1f;--fg:#eceeef;--fg2:#b6bcc1;--muted:#868d92;
--line:#2b3034;--line-strong:#3d434a;--A:#dc3c3c;--C:#c98500;--T:#199e70;--G:#3987e5;--warn:#e8a04a;--ok:#4cc27a;--show-light:none;--show-dark:block;color-scheme:dark}}
:root[data-theme=dark]{--bg:#121415;--surface:#1a1d1f;--fg:#eceeef;--fg2:#b6bcc1;--muted:#868d92;--line:#2b3034;--line-strong:#3d434a;
--A:#dc3c3c;--C:#c98500;--T:#199e70;--G:#3987e5;--warn:#e8a04a;--ok:#4cc27a;--show-light:none;--show-dark:block;color-scheme:dark}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:16px;line-height:1.55;
padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:0 64px}
.wrap{max-width:1120px;margin:0 auto}.prose{max-width:68ch}
h1{font-size:clamp(28px,4vw,40px);font-weight:600;line-height:1.1;letter-spacing:-.01em;margin:40px 0 8px;text-wrap:balance}
h2{font-size:22px;font-weight:600;margin:48px 0 10px;text-wrap:balance}h3{font-size:16px;font-weight:600;margin:22px 0 6px}p{margin:0 0 12px}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0}
.byline{color:var(--fg2);font-size:14px;margin:0 0 24px}.mono{font-family:var(--mono);font-size:.92em}
.verdict{border-left:3px solid var(--fg);padding:4px 0 4px 18px;margin:20px 0 28px;font-size:18px;line-height:1.45;max-width:72ch}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:0 0 8px}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:14px 16px;min-width:0}
.stat .k{font-family:var(--mono);font-size:12px;color:var(--muted);letter-spacing:.04em;text-transform:uppercase}
.stat .v{font-size:34px;font-weight:600;line-height:1.1;margin:6px 0 4px}.stat .d{font-size:13px;color:var(--fg2)}
.base{display:inline-block;width:.95em;height:.95em;border-radius:2px;vertical-align:-.12em;margin-right:.35em}
.bA{background:var(--A)}.bC{background:var(--C)}.bT{background:var(--T)}.bG{background:var(--G)}
figure{margin:18px 0 26px}figure img{display:block;width:100%;height:auto;border-radius:4px;max-width:100%}
figure.img img{background:var(--img-bg)}figure img.light{display:var(--show-light)}figure img.dark{display:var(--show-dark)}
figcaption{font-size:13.5px;color:var(--fg2);margin-top:8px;max-width:80ch;line-height:1.5}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media (max-width:640px){.pair{grid-template-columns:1fr}}
.tablewrap{overflow-x:auto;margin:14px 0 18px}table{border-collapse:collapse;font-size:14px;min-width:420px}
th,td{padding:7px 12px;text-align:right;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums;white-space:nowrap}
th{font-weight:500;color:var(--fg2);font-family:var(--mono);font-size:12px;letter-spacing:.03em}th:first-child,td:first-child{text-align:left}
td.rowhead{font-weight:600}.cell{display:inline-block;min-width:3.2em;padding:2px 6px;border-radius:3px}
ul,ol{padding-left:22px;margin:0 0 12px}li{margin:0 0 8px}
.check{display:grid;grid-template-columns:150px 1fr;gap:6px 18px;padding:12px 0;border-top:1px solid var(--line)}
.check:last-child{border-bottom:1px solid var(--line)}.check .tag{font-family:var(--mono);font-size:12px;letter-spacing:.04em;text-transform:uppercase;padding-top:3px}
.check .tag.flag{color:var(--warn)}.check .tag.ok{color:var(--ok)}.check .body{min-width:0}.check .body p:last-child{margin-bottom:0}
@media (max-width:560px){.check{grid-template-columns:1fr}}.note{font-size:14px;color:var(--fg2)}
"""


def _img_src(path: str, inline: bool) -> str:
    if not inline:
        return os.path.basename(path)
    with open(path, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


def _fig(out: str, stem: str, inline: bool, cls: str = "", alt: str = "", caption: str = "") -> str:
    """One figure; uses <stem>_light/_dark.png pairs when present, else <stem>.png."""
    light, dark, single = (os.path.join(out, f"{stem}_{t}.png") for t in ("light", "dark", "x"))
    single = os.path.join(out, f"{stem}.png")
    imgs = ""
    if os.path.exists(light):
        imgs += f'<img class="light" src="{_img_src(light, inline)}" alt="{html.escape(alt)}">'
        if os.path.exists(dark):
            imgs += f'<img class="dark" src="{_img_src(dark, inline)}" alt="">'
    elif os.path.exists(single):
        imgs += f'<img src="{_img_src(single, inline)}" alt="{html.escape(alt)}">'
    else:
        return ""
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return f'<figure class="{cls}">{imgs}{cap}</figure>'


def _swatch(b: str) -> str:
    return f'<span class="base b{b}"></span>{b}'


def _pct(x) -> str:
    return "–" if x is None else f"{x * 100:.0f}%"


def checks(stats: dict, chastity_cut: float) -> list[tuple[str, bool, str]]:
    """(tag, flagged, text) items computed from stats."""
    out = []
    c = stats["contrast"]
    for pair, v in (("A/C", c["AC"]), ("T/G", c["TG"])):
        flagged = v < 2.0
        out.append((f"{pair} contrast", flagged,
                    f"{v:.2f}×. " + ("Below 2: the two dyes differ little in their channel ratio; expect low chastity on this pair."
                                     if flagged else "Comfortable separation within the pair." if v >= 3 else
                                     "Usable but limited; chastity on this pair will be lower than the other.")))
    sat = []
    for lab, f in stats["fields"].items():
        for k, n in enumerate(f["saturated_px"]):
            if n > 100:
                sat.append(f"{lab}: {BASES[k]} {n:,} px")
    out.append(("saturation", bool(sat), ("Clipped pixels (excluded from the analysis): " + "; ".join(sat) + ". Reduce that channel's exposure or power.")
                if sat else "No channel clips more than 100 pixels in any field."))
    shifts = []
    for lab, f in stats["fields"].items():
        if f.get("shifts_px"):
            mx = max(max(abs(dy), abs(dx)) for dy, dx in f["shifts_px"])
            if mx > 1.0:
                shifts.append(f"{lab}: {mx:.1f} px")
    out.append(("registration", bool(shifts), ("Channel shift above 1 px: " + "; ".join(shifts) + ". Register channels before unmixing.")
                if shifts else "Every channel within 1 px of channel A in every field."))
    nc = {lab: f["no_call_frac"] for lab, f in stats["fields"].items()}
    worst = max(nc.values()) if nc else 0
    out.append(("no-call rate", worst > 0.2, ", ".join(f"{lab} {v * 100:.0f}%" for lab, v in nc.items())
                + f" of blocks below chastity {chastity_cut}." + (" Above 20% somewhere: look at the no-call crops below." if worst > 0.2 else "")))
    M = stats["matrix"]["values"]
    leak_red = max((M[0][2] + M[0][3]) / (M[0][0] + M[0][1]), (M[1][2] + M[1][3]) / (M[1][0] + M[1][1]))
    leak_grn = max((M[2][0] + M[2][1]) / (M[2][2] + M[2][3]), (M[3][0] + M[3][1]) / (M[3][2] + M[3][3]))
    out.append(("cross-pair leak", max(leak_red, leak_grn) > 0.35,
                f"Signal in the other laser pair relative to the own pair: up to {leak_red * 100:.0f}% for A/C dyes, {leak_grn * 100:.0f}% for T/G dyes. "
                + ("High; consistent with autofluorescence or residual dye from a previous cycle." if max(leak_red, leak_grn) > 0.35 else
                   "Unmixes cleanly within one cycle; track it across cycles.")))
    return out


def verdict(stats: dict) -> str:
    c = stats["contrast"]
    per_base = [f["per_base"][b]["pass_frac"] or 0 for f in stats["fields"].values() for b in BASES]
    worst_pass = min(per_base) if per_base else 0
    if min(c["AC"], c["TG"]) >= 2 and worst_pass >= 0.7:
        head = "All four bases are separable."
    elif min(c["AC"], c["TG"]) >= 1.3 and worst_pass >= 0.5:
        head = "The four bases separate, with limited margin."
    else:
        head = "The four bases do not separate reliably."
    weak = "T/G" if c["TG"] < c["AC"] else "A/C"
    return (f"<strong>{head}</strong> Within-pair contrast is {c['AC']:.1f}× for A/C and {c['TG']:.1f}× for T/G; "
            f"{weak} is the weaker pair. Lowest per-base pass rate at the chastity cut is {worst_pass * 100:.0f}%.")


def render(out: str, title: str = "SBS base separability", notes: str | None = None, inline: bool = True, fragment: bool = False) -> str:
    stats = json.load(open(os.path.join(out, "stats.json")))
    p = stats["params"]; cut = p["chastity_cut"]; M = stats["matrix"]["values"]; c = stats["contrast"]; ang = stats["signature_angles_deg"]
    fields = stats["fields"]; labels = list(fields)
    first = fields[labels[0]]
    px = first.get("pixel_um")
    byline = (f"{len(labels)} field{'s' if len(labels) != 1 else ''}: {', '.join(labels)}. Channels: {', '.join(first['channel_names'])}. "
              + (f"{px} µm/px. " if px else "") + f"Block {p['block']} px. Generated {_dt.date.today().isoformat()} by sbs-qc.")
    passes = [f["pass_frac"][str(cut)] for f in fields.values()]
    shifts_max = max((max(max(abs(dy), abs(dx)) for dy, dx in f["shifts_px"]) for f in fields.values() if f.get("shifts_px")), default=None)
    h = []
    h.append(f'<div class="wrap"><p class="eyebrow">sbs-qc · sequencing-by-synthesis base-separability QC</p><h1>{html.escape(title)}</h1>'
             f'<p class="byline">{html.escape(byline)}</p>')
    h.append(f'<div class="verdict">{verdict(stats)}</div>')
    h.append('<div class="stats">'
             f'<div class="stat"><div class="k">A vs C contrast</div><div class="v">{c["AC"]:.1f}×</div><div class="d">ratio of the two dyes\' C/A channel ratios; exposure-independent</div></div>'
             f'<div class="stat"><div class="k">T vs G contrast</div><div class="v">{c["TG"]:.1f}×</div><div class="d">ratio of the two dyes\' G/T channel ratios</div></div>'
             f'<div class="stat"><div class="k">Chastity ≥ {cut}</div><div class="v">{min(passes) * 100:.0f}–{max(passes) * 100:.0f}%</div><div class="d">of blocks pass, per field</div></div>'
             + (f'<div class="stat"><div class="k">Channel registration</div><div class="v">{shifts_max:.1f} px</div><div class="d">largest shift from channel A</div></div>' if shifts_max is not None else "")
             + '</div>')
    h.append('<h2>Checks</h2>')
    for tag, flagged, text in checks(stats, cut):
        h.append(f'<div class="check"><div class="tag {"flag" if flagged else "ok"}">{"flag · " if flagged else "ok · "}{html.escape(tag)}</div><div class="body"><p>{html.escape(text)}</p></div></div>')
    if notes:
        h.append('<div class="prose"><h2>Notes</h2>')
        for para in [x.strip() for x in notes.split("\n\n") if x.strip()]:
            lines = para.split("\n")
            if all(l.lstrip().startswith("- ") for l in lines):
                h.append("<ul>" + "".join(f"<li>{html.escape(l.lstrip()[2:])}</li>" for l in lines) + "</ul>")
            else:
                h.append(f"<p>{html.escape(para)}</p>")
        h.append("</div>")
    h.append('<h2>One colony per base, all four channels on one scale</h2>')
    for lab in labels:
        h.append(_fig(out, f"colonies_{lab}", inline, "img", f"colonies {lab}",
                      f"{html.escape(lab)}: each row is one high-chastity colony called that base; the four grey panels share one intensity ceiling. Composite colours: {_swatch('A')}, {_swatch('C')}, {_swatch('T')}, {_swatch('G')}."))
    h.append('<div class="prose"><h2>Dye signatures</h2><p>Median response of each called base in each channel, pooled over all fields, each row scaled to its brightest channel. Seed blocks per base: '
             + ", ".join(f"{b} {n:,}" for b, n in zip(BASES, stats["seed_counts"])) + '.</p></div><div class="tablewrap"><table><thead><tr><th>base</th>'
             + "".join(f"<th>{b} channel</th>" for b in BASES) + '</tr></thead><tbody>')
    for k in range(4):
        h.append(f'<tr><td class="rowhead">{_swatch(BASES[k])}</td>' + "".join(
            f'<td><span class="cell" style="background:rgba(125,133,139,{0.42 * M[k][j]:.2f})">{M[k][j]:.2f}</span></td>' for j in range(4)) + '</tr>')
    h.append('</tbody></table></div><div class="prose"><p>'
             f'Angles between signature vectors: A–C {ang["AC"]:.0f}°, T–G {ang["TG"]:.0f}°, A–T {ang["AT"]:.0f}°, C–G {ang["CG"]:.0f}°. Angles depend on exposure balance; the contrast ratios and chastity do not.</p></div>')
    h.append('<h2>Within-pair separation</h2>' + _fig(out, "pairs", inline, "", "within-pair histograms",
             "Mixing angle = atan2 of the second channel over the first, so 0° is pure first channel and 90° pure second. Left: red-pair blocks split by A/C angle. Right: green-pair blocks split by T/G angle. Coloured by called base."))
    h.append('<h2>All four at once</h2>' + _fig(out, "scatter", inline, "", "block scatter",
             f"Every block, coloured by called base and faded below chastity {cut}. Read it as a plus sign: for A and C blocks only the horizontal position carries information, for T and G blocks only the vertical. Rings mark the signature positions. The faint cloud at the crossing is the no-call zone."))
    h.append('<h2>Call quality</h2>' + _fig(out, "chastity", inline, "", "chastity histograms",
             "Chastity after non-negative unmixing: top weight divided by the sum of the top two, per called base, log scale."))
    h.append('<div class="tablewrap"><table><thead><tr><th>field</th><th>blocks</th>' + "".join(f"<th>called {b}</th>" for b in BASES)
             + f'<th>median chastity</th><th>pass ≥ {cut}</th><th>pass ≥ 0.8</th><th>no call</th></tr></thead><tbody>')
    for lab, f in fields.items():
        h.append(f'<tr><td class="rowhead">{html.escape(lab)}</td><td>{f["n_blocks"]:,}</td>' + "".join(f"<td>{_pct(x)}</td>" for x in f["call_frac"])
                 + f'<td>{f["chastity_median"]:.2f}</td><td>{_pct(f["pass_frac"][str(cut)])}</td><td>{_pct(f["pass_frac"]["0.8"])}</td><td>{_pct(f["no_call_frac"])}</td></tr>')
    h.append('</tbody></table></div><div class="tablewrap"><table><thead><tr><th>per base, pass ≥ ' + str(cut) + '</th>' + "".join(f"<th>{_swatch(b)}</th>" for b in BASES) + '</tr></thead><tbody>')
    for lab, f in fields.items():
        h.append(f'<tr><td class="rowhead">{html.escape(lab)}</td>' + "".join(f'<td>{_pct(f["per_base"][b]["pass_frac"])}</td>' for b in BASES) + '</tr>')
    h.append('<tr><td class="rowhead">median chastity</td>' + "".join(
        "<td>" + "–".join(sorted({f"{f['per_base'][b]['chastity_median']:.2f}" for f in fields.values() if f["per_base"][b]["chastity_median"] is not None})[::max(1, len(fields) - 1)]) + "</td>" for b in BASES) + '</tr></tbody></table></div>')
    h.append('<h2>Call maps</h2>')
    for lab in labels:
        cm, co = os.path.join(out, f"callmap_{lab}.png"), os.path.join(out, f"composite_{lab}.png")
        if os.path.exists(cm) and os.path.exists(co):
            h.append(f'<figure class="img"><div class="pair"><img src="{_img_src(cm, inline)}" alt="call map {html.escape(lab)}"><img src="{_img_src(co, inline)}" alt="composite {html.escape(lab)}"></div>'
                     f'<figcaption>{html.escape(lab)}. Left: block calls ({_swatch("A")}, {_swatch("C")}, {_swatch("T")}, {_swatch("G")}), dimmed below chastity {cut}. Right: raw composite in the same colours.</figcaption></figure>')
    nc = "".join(_fig(out, f"nocall_{lab}", inline, "img", f"no-call region {lab}", f"{html.escape(lab)}: largest connected low-chastity region, base channels on one scale.") for lab in labels)
    if nc:
        h.append('<h2>No-call regions</h2>' + nc)
    h.append('<div class="prose"><h2>Method</h2><p class="note">'
             f'Background: per-channel 1st percentile. Smoothing: Gaussian σ = {p["sigma"]} px. Foreground: max base channel above {p["fg_thresh"]:.0f} counts, excluding pixels at or above {p["ceiling"]}. '
             f'Blocks: {p["block"]} × {p["block"]} px with at least {p["min_fg"] * 100:.0f}% foreground. Seeds: red-pair fraction above {p["red_hi"]} or below {p["red_lo"]}, 2-means split on the within-pair angle, {p["trim"] * 100:.0f}% of each group nearest the boundary dropped. '
             f'Signature = median normalised vector per seed group, pooled over fields. Calls: non-negative least squares, largest weight; chastity = top / (top + second), cut {cut}. '
             'The matrix is estimated from the same data it scores, so pass rates are an upper bound. No phasing correction applies within one cycle.</p></div></div>')
    body = "\n".join(h)
    if fragment:
        return f"<title>{html.escape(title)}</title>\n<style>{CSS}</style>\n{body}"
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">'
            f'<style>{CSS}</style></head><body>{body}</body></html>')


def write_report(out: str, title: str = "SBS base separability", notes_path: str | None = None, inline: bool = True,
                 fragment: bool = False, filename: str = "report.html") -> str:
    notes = open(notes_path).read() if notes_path else None
    path = os.path.join(out, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render(out, title, notes, inline, fragment))
    return path
