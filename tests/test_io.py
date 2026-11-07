import numpy as np
import tifffile
from sbs_qc.io import load_ome, map_channels
from synth import make_field, NAMES


def test_map_channels_by_suffix():
    idx, dapi = map_channels(NAMES)
    assert idx == {"A": 0, "C": 1, "T": 2, "G": 3} and dapi == 4


def test_map_channels_override_order():
    idx, dapi = map_channels(["DAPI", "G", "T", "C", "A"])
    assert idx == {"A": 4, "C": 3, "T": 2, "G": 1} and dapi == 0


def test_load_ome_roundtrip(tmp_path):
    stack, _ = make_field(seed=3, size=256, n_col=8)
    path = tmp_path / "f.ome.tiff"
    tifffile.imwrite(path, stack.data, metadata={"axes": "CYX", "Channel": {"Name": NAMES},
                                                 "PhysicalSizeX": 0.752, "PhysicalSizeXUnit": "µm"})
    s = load_ome(str(path))
    assert s.data.shape == stack.data.shape and s.data.dtype == np.uint16
    assert s.base_idx == {"A": 0, "C": 1, "T": 2, "G": 3} and s.dapi_idx == 4
    assert s.pixel_um == 0.752
    assert s.base.shape == (4, 256, 256)


def test_load_ome_channels_override(tmp_path):
    stack, _ = make_field(seed=4, size=128, n_col=4)
    path = tmp_path / "noname.ome.tiff"
    tifffile.imwrite(path, stack.data, metadata={"axes": "CYX"})
    s = load_ome(str(path), channels="A,C,T,G,DAPI")
    assert s.base_idx["G"] == 3 and s.dapi_idx == 4
