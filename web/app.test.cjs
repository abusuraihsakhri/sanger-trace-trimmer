const test = require('node:test');
const assert = require('node:assert/strict');
const { mottBounds, trimRead, parseFastq, parseAb1 } = require('./app.js');

test('Mott preserves highest-scoring interval and discards low quality', () => {
  assert.deepEqual(mottBounds([2, 3, 30, 35, 30, 2], 20), [2, 5]);
  assert.deepEqual(mottBounds([0, 0, 0], 20), [0, 0]);
  assert.deepEqual(mottBounds([40, 40], 20), [0, 2]);
});
test('quality controls validate Phred and cutoff values', () => {
  assert.throws(() => mottBounds([94], 20));
  assert.throws(() => mottBounds([1], NaN));
  assert.throws(() => trimRead('x', 'ZZ', [40, 40]));
});
test('FASTQ parsing, trimming, Q30 and ambiguous fraction', () => {
  const parsed = parseFastq('@read\nNNACGN\n+\n!!IIII\n');
  const r = trimRead(...parsed[0]);
  assert.equal(r.sequence, 'ACGN');
  assert.equal(r.start, 2);
  assert.equal(r.q30_fraction, 1);
  assert.equal(r.ambiguous_fraction, .25);
});
test('FASTQ rejects truncated and inconsistent input', () => {
  assert.throws(() => parseFastq('@x\nAC\n+\nI\n'));
  assert.throws(() => parseFastq('@x\nAC\n+\n'));
});
test('ABIF directory reads PBAS2 and PCON2', () => {
  const buffer = new ArrayBuffer(140), dv = new DataView(buffer);
  function ascii(offset, word) {
    for (let i = 0; i < word.length; i++) dv.setUint8(offset + i, word.charCodeAt(i));
  }
  ascii(0,'ABIF');
  dv.setUint32(18,2); dv.setUint32(26,40);
  ascii(40,'PBAS'); dv.setUint32(44,2); dv.setUint32(56,5); dv.setUint32(60,100);
  ascii(68,'PCON'); dv.setUint32(72,2); dv.setUint32(84,5); dv.setUint32(88,120);
  ascii(100,'NNACG');
  [2,2,35,35,35].forEach((v,i)=>dv.setUint8(120+i,v));
  const read = parseAb1(buffer, 'example');
  assert.equal(read[0][1], 'NNACG');
  assert.equal(trimRead(...read[0]).sequence, 'ACG');
  assert.throws(() => parseAb1(new ArrayBuffer(8)));
});
