'use strict';

function mottBounds(qualities, cutoffQ = 20) {
  if (!Number.isFinite(cutoffQ) || cutoffQ < 0 || cutoffQ > 60)
    throw new Error('Mott cutoff must be Q0–Q60.');
  const threshold = Math.pow(10, -cutoffQ / 10);
  let score = 0, best = 0, currentStart = 0, left = 0, right = 0;
  qualities.forEach((q, i) => {
    if (!Number.isInteger(q) || q < 0 || q > 93)
      throw new Error('Phred quality must be an integer from 0 to 93.');
    score += threshold - Math.pow(10, -q / 10);
    if (score > best + 1e-12) { best = score; left = currentStart; right = i + 1; }
    if (score < 0) { score = 0; currentStart = i + 1; }
  });
  return [left, right];
}

function trimRead(name, sequence, qualities, cutoffQ = 20, minLength = 1) {
  if (!Number.isInteger(minLength) || minLength < 1 || minLength > 1000000)
    throw new Error('Minimum length must be between 1 and 1,000,000.');
  if (!sequence || sequence.length !== qualities.length || !/^[ACGTRYSWKMBDHVN]+$/i.test(sequence))
    throw new Error('Sequence must contain valid IUPAC bases and matching Phred scores.');
  let [start, end] = mottBounds(qualities, cutoffQ);
  if (end - start < minLength) [start, end] = [0, 0];
  const trimmed = sequence.slice(start, end), qs = qualities.slice(start, end);
  const n = trimmed.length;
  return {
    name, start, end, original_length: sequence.length,
    trimmed_length: n, sequence: trimmed, qualities: qs,
    q20_fraction: n ? qs.filter(q => q >= 20).length / n : 0,
    q30_fraction: n ? qs.filter(q => q >= 30).length / n : 0,
    ambiguous_fraction: n ? [...trimmed].filter(b => !/[ACGT]/i.test(b)).length / n : 0,
    original_qualities: qualities
  };
}

function parseFastq(input) {
  const lines = input.replace(/\r\n?/g, '\n').split('\n');
  if (lines.at(-1) === '') lines.pop();
  if (!lines.length || lines.length % 4) throw new Error('FASTQ requires complete four-line records.');
  const records = [];
  for (let i = 0; i < lines.length; i += 4) {
    const [header, seq, separator, encoded] = lines.slice(i, i + 4);
    if (!header.startsWith('@') || header.length === 1 || !separator.startsWith('+') ||
        !seq || seq.length !== encoded.length)
      throw new Error('Malformed FASTQ record ' + (i / 4 + 1) + '.');
    const qs = [...encoded].map(c => c.charCodeAt(0) - 33);
    if (qs.some(q => q < 0 || q > 93))
      throw new Error('Invalid Phred+33 quality in FASTQ record ' + (i / 4 + 1) + '.');
    records.push([header.slice(1), seq, qs]);
    if (records.length > 5000) throw new Error('Batch limit is 5,000 reads.');
  }
  return records;
}

function parseAb1(buffer, name = 'trace') {
  const dv = new DataView(buffer);
  const decoder = new TextDecoder('ascii');
  if (dv.byteLength < 34 || decoder.decode(new Uint8Array(buffer, 0, 4)) !== 'ABIF')
    throw new Error('File is not an ABI/AB1 chromatogram.');
  const u32 = offset => dv.getUint32(offset, false);
  const directoryCount = u32(18), directoryOffset = u32(26);
  if (directoryCount > 10000 || directoryOffset < 34 ||
      directoryOffset + directoryCount * 28 > dv.byteLength)
    throw new Error('Invalid ABI directory.');
  const entries = new Map();
  for (let i = 0; i < directoryCount; i++) {
    const at = directoryOffset + i * 28;
    const tag = decoder.decode(new Uint8Array(buffer, at, 4));
    const size = u32(at + 16);
    const offset = size <= 4 ? at + 20 : u32(at + 20);
    if (size > 10000000 || offset > dv.byteLength || size > dv.byteLength - offset)
      throw new Error('Invalid ABI data offset or size.');
    entries.set(tag + u32(at + 4), new Uint8Array(buffer, offset, size));
  }
  const called = entries.get('PBAS2') || entries.get('PBAS1');
  const confidence = entries.get('PCON2') || entries.get('PCON1');
  if (!called || !confidence) throw new Error('Missing PBAS/PCON base calls and quality data.');
  const sequence = decoder.decode(called).replace(/\0+$/, '');
  if (sequence.length !== confidence.length) throw new Error('AB1 base/quality lengths differ.');
  return [[name, sequence, Array.from(confidence)]];
}

if (typeof module !== 'undefined' && module.exports)
  module.exports = { mottBounds, trimRead, parseFastq, parseAb1 };

if (typeof document !== 'undefined') {
  const el = id => document.getElementById(id);
  const MAX_SIZE = 10 * 1024 * 1024;
  let output = [];
  const fraction = n => (n * 100).toFixed(1) + '%';

  function render() {
    el('empty').hidden = true;
    el('results').hidden = false;
    el('read-count').textContent = String(output.length);
    el('retained-count').textContent = String(output.filter(r => r.trimmed_length).length);
    el('base-count').textContent = String(output.reduce((s, r) => s + r.trimmed_length, 0));
    el('table-body').replaceChildren();
    el('choose-read').replaceChildren();
    output.forEach((read, index) => {
      const option = document.createElement('option');
      option.value = String(index); option.textContent = read.name;
      el('choose-read').appendChild(option);
      const row = document.createElement('tr');
      for (const value of [read.name, read.original_length, read.trimmed_length,
                           fraction(read.q20_fraction), fraction(read.q30_fraction),
                           fraction(read.ambiguous_fraction)]) {
        const cell = document.createElement('td');
        cell.textContent = String(value);
        row.appendChild(cell);
      }
      el('table-body').appendChild(row);
    });
    showSelected();
  }

  function showSelected() {
    const r = output[Number(el('choose-read').value)];
    if (!r) return;
    el('sequence').textContent = r.sequence || '(no bases retained)';
    el('coordinates').textContent =
      'Retained [' + r.start + ', ' + r.end + ') of ' + r.original_length +
      ' bases · Q20 ' + fraction(r.q20_fraction) + ' · Q30 ' + fraction(r.q30_fraction);
  }

  async function run() {
    el('error').textContent = '';
    output = []; el('results').hidden = true; el('empty').hidden = false;
    try {
      const cutoff = Number(el('cutoff').value), minLength = Number(el('min-length').value);
      if (!Number.isFinite(cutoff) || cutoff < 0 || cutoff > 60)
        throw new Error('Mott cutoff must be Q0–Q60.');
      if (!Number.isInteger(minLength) || minLength < 1 || minLength > 1000000)
        throw new Error('Minimum length must be between 1 and 1,000,000.');
      const file = el('file').files[0];
      let records;
      if (file) {
        if (file.size > MAX_SIZE) throw new Error('File is larger than 10 MB.');
        if (/\.(ab1|abi)$/i.test(file.name)) {
          records = parseAb1(await file.arrayBuffer(), file.name.replace(/\.[^.]+$/, ''));
        } else if (/\.(fastq|fq)$/i.test(file.name)) {
          records = parseFastq(await file.text());
        } else throw new Error('Choose .ab1, .abi, .fastq, or .fq file.');
      } else {
        const input = el('paste').value;
        if (new Blob([input]).size > MAX_SIZE) throw new Error('Input is larger than 10 MB.');
        if (!input.trim()) throw new Error('Choose a file or paste a FASTQ record.');
        records = parseFastq(input);
      }
      output = records.map(([name, seq, qs]) => trimRead(name, seq, qs, cutoff, minLength));
      render();
    } catch (err) { el('error').textContent = err.message || String(err); }
  }

  function download(kind) {
    if (!output.length) return;
    let data, filename, mime = 'text/plain;charset=utf-8';
    if (kind === 'json') {
      data = JSON.stringify(output.map(({ sequence, qualities, original_qualities, ...qc }) => qc), null, 2) + '\n';
      filename = 'sanger-qc.json'; mime = 'application/json';
    } else {
      data = output.map(r => {
        const name = r.name.replace(/[\r\n]/g, ' ');
        if (kind === 'fasta')
          return '>' + name + ' start=' + r.start + ' end=' + r.end + '\n' + r.sequence + '\n';
        return '@' + name + '\n' + r.sequence + '\n+\n' +
          r.qualities.map(q => String.fromCharCode(q + 33)).join('') + '\n';
      }).join('');
      filename = 'sanger-trimmed.' + kind;
    }
    const url = URL.createObjectURL(new Blob([data], { type: mime }));
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = filename; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  el('run').addEventListener('click', run);
  el('example').addEventListener('click', () => {
    el('file').value = '';
    el('paste').value = '@sample-1\nNNACGTACGTNN\n+\n!!IIIIIIII!!\n@sample-2\nCCGTTNNAA\n+\nIIIII!!II\n';
    el('error').textContent = '';
  });
  el('choose-read').addEventListener('change', showSelected);
  for (const kind of ['fasta', 'fastq', 'json'])
    el('download-' + kind).addEventListener('click', () => download(kind));
}
