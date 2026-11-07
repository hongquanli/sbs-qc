import json, os
import tifffile
from sbs_qc.cli import main
from synth import make_field, NAMES


def test_analyze_smoke(tmp_path):
    paths = []
    for s in (0, 1):
        st, _ = make_field(seed=s, size=384, n_col=10)
        p = tmp_path / f"f{s}.ome.tiff"
        tifffile.imwrite(p, st.data, metadata={"axes": "CYX", "Channel": {"Name": NAMES}})
        paths.append(str(p))
    out = tmp_path / "res"
    assert main(["analyze", *paths, "--out", str(out), "--themes", "light"]) == 0
    stats = json.load(open(out / "stats.json"))
    assert set(stats["fields"]) == {"f0", "f1"}
    assert os.path.exists(out / "matrix.csv")
    for f in ["pairs_light.png", "scatter_light.png", "chastity_light.png", "colonies_f0.png", "callmap_f0.png", "composite_f1.png"]:
        assert os.path.exists(out / f), f
