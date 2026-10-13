# Sanger Trace Trimmer

Quality-based trimming of Sanger sequencing reads from ABI/AB1 chromatograms or Phred+33 FASTQ records. An independent static browser application is available in the `web/` directory. GitHub Pages deployment is configured; see the repository's **Deploy browser application** workflow for deployment status.

## Features

- **Mott trimming:** retain the contiguous segment with the highest cumulative score, using P(error at cutoff) − P(error per base). Defaults to Q20, with a configurable minimum retained length.
- **Read-level QC:** zero-based start/end-exclusive boundaries, retained length, Q20 and Q30 fractions, and ambiguous IUPAC-base fraction.
- **Inputs:** AB1/ABI base calls and PCON qualities, or four-line Phred+33 FASTQ.
- **Outputs:** FASTA, FASTQ (retaining Phred scores), and JSON QC summaries. Reads failing the minimum-length filter remain in the report but are omitted from sequence exports.
- **Offline browser use:** the static app reads and processes files locally; there is no upload endpoint or external script dependency.

This tool **does not perform vector alignment, trace peak re-calling, base-call correction, or clinical validation**. Inspect chromatograms and align sequence as appropriate before interpreting results.

## Browser

Open `web/index.html` from an HTTP static server, or use the GitHub Pages deployment once it has succeeded.

```bash
python -m http.server 8000 --directory web
```

Visit http://127.0.0.1:8000. Select a .ab1/.abi or .fastq/.fq file, or paste FASTQ data, set the Q threshold and minimum length, and select **Trim & analyze**. Use **Load example** for a test dataset. Downloads are generated within the browser tab. Modern Chromium, Firefox, and Safari with JavaScript and File APIs are expected; automated cross-browser verification has not been completed.

**Data handling:** Input files and identifiers stay in the browser for this static app; no server is contacted. Browser downloads save results to the local device. The separately hosted FastAPI service is a different interface.

## Python CLI

Python 3.10+:

```bash
python -m pip install -e ".[trace]"
sanger-trim input.ab1 --output trimmed.fasta --cutoff-q 20 --min-length 100 --report qc.json
sanger-trim reads.fastq --output trimmed.fastq --format fastq --report qc.json
```

The `[trace]` extra installs Biopython for ABI/AB1 reading. FASTQ trimming uses only Python's standard library. You can also run `python -m trace_quality` without installing the package, provided its runtime dependencies are present. Output coordinates are 0-based, end-exclusive. A read without a positive-scoring segment is rejected (retained length 0).

## Legacy interfaces

The repository also retains the pre-existing generic `sanger_trim.py` lookup/CSV tool, and the separately simulated supervisor CLI and FastAPI server for backward compatibility:

```bash
python -m sanger_trim single creatinine
sanger-trace-trimmer audit --task-id EXAMPLE-001
sanger-trace-trimmer serve --host 127.0.0.1 --port 8000
```

These legacy interfaces **are not a Sanger quality trimmer**. The supervisor uses a mock model, and its audit criteria are generic illustrative thresholds, not validated CAP/CLSI decision rules. The in-memory HMAC audit trail requires `AUDIT_SECRET_KEY` for persistent production identity; it is not durable across service restarts and is not a substitute for a compliance-grade audit system. The API should not be publicly exposed without appropriate network access controls and authentication.

## Development and tests

```bash
python -m pip install -e ".[dev,trace]"
python -m pytest -q
node --test web/app.test.cjs
```

GitHub Actions tests Python 3.10–3.12, verifies import/compilation, runs targeted linting, and tests the browser trimming logic using Node. Static website deployment uses the `web/` directory. Docker support remains available for the legacy API, but Compose requires an explicitly configured, securely generated `AUDIT_SECRET_KEY`.

## License

MIT; see [LICENSE](LICENSE).
