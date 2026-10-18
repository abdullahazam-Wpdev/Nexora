// Retain the verified signed package using REA's own publisher-cache procedure.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { LinuxHopperPublisher } from '../.tools/rea/node_modules/rea-agents/dist/application/LinuxHopperPublisher.js';

const publisher = new LinuxHopperPublisher(process.env, async () => 'arch');
try {
  const release = JSON.parse(readFileSync('tooling/hopper/releases-6.6.0.json', 'utf8')).Arch;
  const archive = resolve('.tools/downloads/Hopper-6.6.0-Linux-demo.pkg.tar.xz');
  const proof = await publisher.verifyArchive('arch', release, archive, undefined,
    readFileSync('tooling/hopper/hopper-public-key.asc', 'utf8'));
  if (!proof.ok) throw proof.error;
  const retained = await publisher.retainVerifiedArchive(proof.value, archive);
  if (!retained.ok) throw retained.error;
  console.log(JSON.stringify({ cache: publisher.cacheRoot, sha256: proof.value.packageSha256 }));
} finally {
  await publisher.close();
}
