"""
Tests for sanger_trim core module.
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
import sanger_trim as m


class TestLookup:
    def test_lookup_returns_expected_keys(self):
        r = m.lookup("creatinine")
        assert "top_hit" in r
        assert "score" in r
        assert "query" in r
        assert "all" in r

    def test_lookup_case_insensitive(self):
        r1 = m.lookup("creatinine")
        r2 = m.lookup("CREATININE")
        assert r1["top_hit"] == r2["top_hit"]

    def test_lookup_with_whitespace(self):
        r = m.lookup("  creatinine  ")
        assert r["top_hit"] != "no match"

    def test_lookup_returns_dict_with_all_hits(self):
        r = m.lookup("test")
        assert isinstance(r["all"], list)
        assert len(r["all"]) <= 3

    def test_lookup_empty_string(self):
        r = m.lookup("")
        assert "top_hit" in r
        assert "score" in r


class TestProcessCsv:
    def test_process_csv_basic(self, tmp_path):
        pdir = pathlib.Path(__file__).parent.parent
        input_csv = pdir / "sample.csv"
        output_csv = tmp_path / "test_output.csv"
        rows = m.process_csv(str(input_csv), str(output_csv))
        assert len(rows) >= 1
        assert output_csv.exists()

    def test_process_csv_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            m.process_csv(str(tmp_path / "nonexistent.csv"), str(tmp_path / "out.csv"))

    def test_process_csv_invalid_path(self, tmp_path):
        with pytest.raises(ValueError):
            m.process_csv(str(tmp_path), str(tmp_path / "out.csv"))

    def test_process_csv_creates_output(self, tmp_path):
        pdir = pathlib.Path(__file__).parent.parent
        input_csv = pdir / "sample.csv"
        output_csv = tmp_path / "results.csv"
        m.process_csv(str(input_csv), str(output_csv))
        content = output_csv.read_text()
        assert "top_hit" in content
        assert "lookup_score" in content


class TestMain:
    def test_main_single_query(self, capsys):
        result = m.main(["single", "creatinine"])
        assert result == 0
        captured = capsys.readouterr()
        assert "top_hit" in captured.out

    def test_main_batch(self, tmp_path, capsys):
        pdir = pathlib.Path(__file__).parent.parent
        input_csv = pdir / "sample.csv"
        output_csv = tmp_path / "batch_out.csv"
        result = m.main(["batch", "--input", str(input_csv), "--output", str(output_csv)])
        assert result == 0
        assert output_csv.exists()
