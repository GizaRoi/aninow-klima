import { spawnSync } from 'node:child_process';
import { cpSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const result = spawnSync(process.execPath, [require.resolve('next/dist/bin/next'), 'build', 'apps/web', '--webpack'], {
  cwd: root, stdio: 'inherit', env: { ...process.env, NEXT_TELEMETRY_DISABLED: '1' },
});
if (result.status !== 0) process.exit(result.status ?? 1);
mkdirSync(path.join(root, 'dist'), { recursive: true });
cpSync(path.join(root, 'apps/web/out'), path.join(root, 'dist'), { recursive: true });
console.log('Static prototype built in dist/');
