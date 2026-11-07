import json, os
from html.parser import HTMLParser
import tifffile
from sbs_qc.cli import main
from synth import make_field, NAMES


class _Count(HTMLParser):
    def __init__(self):
        super().__init__(); self.imgs = 0; self.data_uris = 0; self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "img":
            self.imgs += 1
            if dict(attrs).get("src", "").startswith("data:image/png;base64,"):
                self.data_uris += 1


def _run(tmp_path, extra=()):
    paths = []
    for s in (0, 1):
        st, _ = make_field(seed=s, size=384, n_col=10)
        p = tmp_path / f"f{s}.ome.tiff"
        tifffile.imwrite(p, st.data, metadata={"axes": "CYX", "Channel": {"Name": NAMES}})
        paths.append(str(p))
    out = tmp_path / "res"
    assert main(["analyze", *paths, "--out", str(out), "--themes", "light", *extra]) == 0
    return out


def test_report_written_with_analyze(tmp_path):
    notes = tmp_path / "notes.txt"
    notes.write_text("Cycle 1 of the test run.\n\n- first bullet\n- second bullet\n")
    out = _run(tmp_path, ["--title", "Synthetic run", "--notes", str(notes)])
    html = (out / "report.html").read_text()
    stats = json.load(open(out / "stats.json"))
    assert html.startswith("<!doctype html>") and html.rstrip().endswith("</html>")
    assert "<title>Synthetic run</title>" in html
    assert "first bullet" in html and "Cycle 1 of the test run." in html
    m = stats["matrix"]["values"]
    assert f"{m[1][0]:.2f}" in html
    for lab in stats["fields"]:
        assert f"colonies {lab}" in html
    c = _Count(); c.feed(html)
    assert c.imgs >= 8 and c.data_uris == c.imgs


def test_report_command_links_figures(tmp_path):
    out = _run(tmp_path, ["--no-report"])
    assert not os.path.exists(out / "report.html")
    assert main(["report", str(out), "--link-figures", "--fragment"]) == 0
    html = (out / "report.html").read_text()
    assert not html.startswith("<!doctype") and html.startswith("<title>")
    c = _Count(); c.feed(html)
    assert c.imgs >= 8 and c.data_uris == 0
    assert 'src="scatter_light.png"' in html
