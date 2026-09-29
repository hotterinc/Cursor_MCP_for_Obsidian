const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const py = path.join(root, 'python');
const venv = path.join(py, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const [mode, ...args] = process.argv.slice(2);
let command, argv, cwd = root;
const env = { ...process.env };
if (mode === 'desktop') {
  delete env.ELECTRON_RUN_AS_NODE;
  command = 'pnpm'; argv = ['--filter', '@obsidian-context/desktop', 'dev', ...args];
} else if (mode === 'python') {
  cwd = py;
  command = fs.existsSync(venv) ? venv : 'uv';
  argv = fs.existsSync(venv) ? ['-m', 'uv', ...args] : args;
} else if (mode === 'build') {
  command = process.platform === 'win32' ? 'powershell' : 'bash';
  argv = process.platform === 'win32' ? ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', path.join(root, 'scripts/build-plugin-sidecar.ps1')] : [path.join(root, 'scripts/build-plugin-sidecar.sh')];
} else { throw new Error('Unknown runner mode'); }
const result = spawnSync(command, argv, { cwd, env, stdio: 'inherit', shell: process.platform === 'win32' && command === 'pnpm' });
if (result.error) { console.error(result.error.message); process.exit(1); }
if (result.status !== 0) process.exit(result.status ?? 1);
if (mode === 'build' && args.includes('--desktop')) {
  const name = 'obsidian-context-mcp' + (process.platform === 'win32' ? '.exe' : '');
  const destination = path.join(root, 'apps/desktop/resources/python-sidecar');
  fs.mkdirSync(destination, { recursive: true });
  fs.copyFileSync(path.join(root, 'obsidian-plugin/bin', name), path.join(destination, name));
}
