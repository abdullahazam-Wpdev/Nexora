// Test the project MCP wrapper without editing any client registration.
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { writeFileSync } from 'node:fs';
const require = createRequire(new URL('../.tools/rea/package.json', import.meta.url));
const { Client } = await import(require.resolve('@modelcontextprotocol/client'));
const { StdioClientTransport } = await import(require.resolve('@modelcontextprotocol/client/stdio'));
const client = new Client({ name: 'nexora-rea-verifier', version: '1' });
const transport = new StdioClientTransport({command: resolve('scripts/rea.sh'), args: ['mcp'], stderr: 'pipe',
  env: Object.fromEntries(Object.entries(process.env).filter(([, v]) => typeof v === 'string'))});
let stderr = '';
transport.stderr?.on('data', (chunk) => { stderr = (stderr + chunk.toString()).slice(-4096); });
try {
  await client.connect(transport);
  const catalog = await client.listTools();
  const reply = await client.callTool({ name: 'binary_session', arguments: {} });
  if (reply.isError) throw new Error('Session inspection failed');
  const data = reply.structuredContent ?? JSON.parse(reply.content.find(c => c.type === 'text').text);
  const session = data.result ?? data;
  const hopper = session.analysis_provider_candidates.find(p => p.provider.id === 'hopper');
  if (catalog.tools.length !== 207 || hopper.availability.status !== 'available') {
    throw new Error('Unexpected tool count or unavailable Hopper provider');
  }
  const out = { status: 'passed', tools: catalog.tools.length,
    version: session.server_identity.package.version, hopper: hopper.availability,
    config_changed: false };
  writeFileSync('artifacts/rea-project-mcp-verification.json', JSON.stringify(out, null, 2) + '\n');
  console.log(JSON.stringify(out));
} catch (error) {
  writeFileSync('artifacts/rea-project-mcp-stderr.log', stderr);
  throw error;
} finally {
  await client.close();
}
