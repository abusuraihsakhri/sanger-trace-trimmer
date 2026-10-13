"""Quality-based Sanger sequence trimming (Mott maximum-scoring segment).

FASTQ requires no optional dependencies. Reading ABI/AB1 chromatograms requires
Biopython (install the ``trace`` extra). No vector screening is performed.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterator


def mott_bounds(qualities: list[int], cutoff_q: float = 20) -> tuple[int, int]:
    """Return [start, end) maximizing sum(P_error_cutoff - P_error_base).

    The empty segment is returned if no base has positive total score. Ties
    retain the earliest maximal segment. This is not a sliding Q-score filter.
    """
    if not math.isfinite(cutoff_q) or not 0 <= cutoff_q <= 60:
        raise ValueError("cutoff_q must be between 0 and 60")
    cutoff = 10 ** (-cutoff_q / 10)
    score = 0.0
    best = 0.0
    start = 0
    bounds = (0, 0)
    for i, quality in enumerate(qualities):
        if isinstance(quality, bool) or not isinstance(quality, int) or not 0 <= quality <= 93:
            raise ValueError("Phred qualities must be integers between 0 and 93")
        score += cutoff - 10 ** (-quality / 10)
        if score > best + 1e-12:
            best = score
            bounds = (start, i + 1)
        if score < 0:
            score = 0.0
            start = i + 1
    return bounds


def trim_record(name: str, sequence: str, qualities: list[int], cutoff_q: float = 20,
                min_length: int = 1) -> dict:
    """Trim a record and summarize retained-base QC; coordinates are 0-based."""
    if not isinstance(min_length, int) or isinstance(min_length, bool) or min_length < 1:
        raise ValueError("min_length must be a positive integer")
    if not sequence or len(sequence) != len(qualities):
        raise ValueError("Sequence must be nonempty and match quality-array length")
    if any(base.upper() not in "ACGTRYSWKMBDHVN" for base in sequence):
        raise ValueError("Sequence contains invalid IUPAC nucleotide symbols")
    start, end = mott_bounds(qualities, cutoff_q)
    if end - start < min_length:
        start, end = 0, 0
    bases = sequence[start:end]
    qs = qualities[start:end]
    return {
        "name": name,
        "start": start,
        "end": end,
        "original_length": len(sequence),
        "trimmed_length": len(bases),
        "sequence": bases,
        "qualities": qs,
        "q20_fraction": sum(q >= 20 for q in qs) / len(qs) if qs else 0.0,
        "q30_fraction": sum(q >= 30 for q in qs) / len(qs) if qs else 0.0,
        "ambiguous_fraction": sum(base.upper() not in "ACGT" for base in bases) / len(bases) if bases else 0.0,
    }


def read_fastq(path: Path) -> Iterator[tuple[str, str, list[int]]]:
    """Read strict 4-line, Sanger-encoded (Phred+33) FASTQ records."""
    with path.open("r", encoding="ascii", newline=None) as handle:
        index = 0
        while header := handle.readline():
            index += 1
            sequence = handle.readline()
            separator = handle.readline()
            quality = handle.readline()
            if not sequence or not separator or not quality:
                raise ValueError(f"Truncated FASTQ record {index}")
            if not header.startswith("@") or not separator.startswith("+"):
                raise ValueError(f"Invalid FASTQ header/separator in record {index}")
            identifier = header[1:].rstrip("\r\n")
            seq = sequence.rstrip("\r\n")
            qual = quality.rstrip("\r\n")
            if not identifier or len(seq) != len(qual):
                raise ValueError(f"Missing identifier or length mismatch in FASTQ record {index}")
            phred = [ord(c) - 33 for c in qual]
            if any(q < 0 or q > 93 for q in phred):
                raise ValueError(f"Invalid Phred+33 character in record {index}")
            yield identifier, seq, phred


def read_ab1(path: Path) -> Iterator[tuple[str, str, list[int]]]:
    """Read base calls and their basecaller confidence from an ABI chromatogram."""
    try:
        from Bio import SeqIO
    except ImportError as exc:
        raise RuntimeError("AB1 input requires Biopython: pip install '.[trace]'") from exc
    record = SeqIO.read(str(path), "abi")
    seq = str(record.seq)
    qualities = record.letter_annotations.get("phred_quality")
    if not qualities or len(seq) != len(qualities):
        raise ValueError("AB1 lacks matching base calls and Phred quality values")
    yield path.stem, seq, list(qualities)


def write_records(results: list[dict], path: Path, output_format: str) -> None:
    """Write retained bases, preserving quality values in FASTQ exports."""
    if output_format not in {"fasta", "fastq"}:
        raise ValueError("output_format must be fasta or fastq")
    with path.open("w", encoding="ascii", newline="\n") as handle:
        for r in results:
            name = str(r["name"]).replace("\r", " ").replace("\n", " ")
            if output_format == "fasta":
                handle.write(f">{name} start={r['start']} end={r['end']}\n{r['sequence']}\n")
            else:
                encoded = "".join(chr(q + 33) for q in r["qualities"])
                handle.write(f"@{name}\n{r['sequence']}\n+\n{encoded}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trim Sanger AB1 or FASTQ Phred data with Mott scoring")
    parser.add_argument("input", type=Path, help=".ab1/.abi chromatogram or Phred+33 .fastq/.fq")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output FASTA or FASTQ file")
    parser.add_argument("--format", choices=["fasta", "fastq"], default="fasta")
    parser.add_argument("--cutoff-q", type=float, default=20.0)
    parser.add_argument("--min-length", type=int, default=1)
    parser.add_argument("--report", type=Path, help="Write batch QC summary as JSON")
    args = parser.parse_args(argv)
    suffix = args.input.suffix.lower()
    if suffix not in {".ab1", ".abi", ".fastq", ".fq"}:
        parser.error("Input must have .ab1, .abi, .fastq, or .fq extension")
    reader = read_ab1 if suffix in {".ab1", ".abi"} else read_fastq
    try:
        results = [trim_record(*record, cutoff_q=args.cutoff_q, min_length=args.min_length)
                   for record in reader(args.input)]
        if not results:
            raise ValueError("No input records found")
        write_records(results, args.output, args.format)
        report = [{k: v for k, v in r.items() if k not in {"sequence", "qualities"}} for r in results]
        if args.report:
            args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"records": len(results), "retained": sum(r["trimmed_length"] > 0 for r in results), "qc": report}))
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
