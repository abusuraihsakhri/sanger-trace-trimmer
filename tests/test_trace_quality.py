import json
import pytest
from trace_quality import mott_bounds, trim_record, read_fastq, main, write_records


def test_mott_removes_noisy_ends():
    assert mott_bounds([3, 5, 30, 35, 30, 2], 20) == (2, 5)


def test_mott_all_low_or_high():
    assert mott_bounds([0, 0, 0], 20) == (0, 0)
    assert mott_bounds([40, 40, 40], 20) == (0, 3)


def test_trim_qc_and_ambiguity():
    r = trim_record("x", "NNACGN", [2, 2, 32, 32, 32, 2])
    assert r["sequence"] == "ACG"
    assert r["start"] == 2 and r["end"] == 5
    assert r["q20_fraction"] == 1 and r["ambiguous_fraction"] == 0


def test_min_length_and_invalid_inputs():
    assert trim_record("x", "ACGT", [2, 30, 30, 2], min_length=3)["trimmed_length"] == 0
    for qualities in ([94], [-1], [2.0]):
        with pytest.raises(ValueError):
            mott_bounds(qualities)
    with pytest.raises(ValueError):
        trim_record("x", "GG", [30])
    with pytest.raises(ValueError):
        trim_record("x", "Z", [30])
    with pytest.raises(ValueError):
        mott_bounds([10], float("nan"))


def test_fastq_and_export(tmp_path):
    p = tmp_path / "input.fastq"
    p.write_text("@t1\nACGT\n+\n!III\n@t2\nNNAC\n+\n!!II\n")
    records = list(read_fastq(p))
    assert len(records) == 2
    results = [trim_record(*r) for r in records]
    output = tmp_path / "out.fastq"
    write_records(results, output, "fastq")
    assert list(read_fastq(output))[0][1] == "CGT"
    report = tmp_path / "report.json"
    assert main([str(p), "-o", str(tmp_path / "out.fasta"), "--report", str(report)]) == 0
    assert len(json.loads(report.read_text())) == 2


@pytest.mark.parametrize("bad", ["@a\nAC\n+\nI\n", "@a\nAC\n+\n", ">a\nAC\n+\nII\n"])
def test_reject_malformed_fastq(tmp_path, bad):
    p = tmp_path / "bad.fastq"
    p.write_text(bad)
    with pytest.raises(ValueError):
        list(read_fastq(p))
