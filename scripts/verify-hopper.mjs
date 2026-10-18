// Verify official Hopper package bytes before extraction. No target execution.
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { verifyDetachedPgpSignature } from '../.tools/rea/node_modules/rea-agents/dist/process/DetachedPgpSignature.js';

const family = process.argv[2] || 'rpm';
if (!['rpm', 'arch'].includes(family)) throw new Error('Expected rpm or arch');
const release = JSON.parse(readFileSync('tooling/hopper/releases-6.6.0.json', 'utf8'))[family === 'rpm' ? 'Fedora' : 'Arch'];
if (release.version !== '6.6.0' || release.main_exe_hash !== 'b2271008fb82bf14cfae5c3644cdde2b11fc6804bd7c99d67032ec1b1942d53c') {
  throw new Error('Unreviewed Hopper release');
}
const bytes = readFileSync(`.tools/downloads/Hopper-6.6.0-Linux-demo.${family === 'rpm' ? 'rpm' : 'pkg.tar.xz'}`);
if (bytes.length !== Number(release.file_length) || createHash('sha1').update(bytes).digest('hex') !== release.file_hash) {
  throw new Error('Hopper package length or checksum mismatch');
}
const proof = await verifyDetachedPgpSignature(bytes, Buffer.from(release.signature, 'base64'),
  readFileSync('tooling/hopper/hopper-public-key.asc', 'utf8'), '7C2D73BAFAF5B9A710A69DA1A26DF815099B1BCD');
if (!proof.ok) throw proof.error;
console.log(JSON.stringify({ ...proof.value, sha256: createHash('sha256').update(bytes).digest('hex'), bytes: bytes.length }));
