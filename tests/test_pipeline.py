import numpy as np
import pytest
from sbs_qc.pipeline import Params, analyze
from sbs_qc.signatures import contrast_ratios, signature_angles
from synth import make_field, block_truth, M_TRUE


@pytest.fixture(scope="module")
def result():
    stacks, truths = zip(*[make_field(seed=s) for s in (0, 1)])
    an = analyze(list(stacks), Params(registration=False), labels=["s0", "s1"])
    return an, truths


def test_matrix_recovered(result):
    an, _ = result
    assert np.abs(an.M - M_TRUE).max() < 0.08, an.M


def test_contrast_ratios_from_known_matrix():
    c = contrast_ratios(M_TRUE)
    assert c["AC"] == pytest.approx(3.34, abs=0.02)
    assert c["TG"] == pytest.approx(2.42, abs=0.02)
    a = signature_angles(M_TRUE)
    assert a["AC"] > a["TG"] > 10


def test_calls_match_truth(result):
    an, truths = result
    for fr, truth in zip(an.fields, truths):
        bt = block_truth(truth, fr.feats.ok, fr.feats.block)
        m = (bt >= 0) & (fr.chas >= an.params.chastity_cut)
        assert m.sum() > 200
        acc = np.mean(fr.call[m] == bt[m])
        assert acc > 0.97, acc


def test_chastity_pass_rate(result):
    an, _ = result
    for lab, fs in an.stats["fields"].items():
        assert fs["pass_frac"]["0.6"] > 0.9, (lab, fs["pass_frac"])
        for b, pb in fs["per_base"].items():
            assert pb["n"] > 0, (lab, b)


def test_stats_shape(result):
    an, _ = result
    s = an.stats
    assert s["matrix"]["values"][0][0] == 1.0
    assert set(s["fields"]) == {"s0", "s1"}
    assert len(s["fields"]["s0"]["call_frac"]) == 4
