const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const esbuild = require('esbuild');

function load(dependencies) {
  const file = path.join(__dirname, '../src/views/CodexSetupActions.ts');
  const module = new Module(file);
  module.require = id => dependencies[id] ?? require(id);
  module._compile(esbuild.transformSync(fs.readFileSync(file, 'utf8'), { loader: 'ts', format: 'cjs' }).code, file);
  return module.exports;
}

test('config shortcut opens the user config file and falls back to its folder', async () => {
  const opened = [];
  let configExists = true;
  const { openCodexConfig } = load({
    electron: { shell: { openPath: async target => { opened.push(target); return ''; } } },
    fs: { existsSync: () => configExists },
    os: { homedir: () => 'C:\\Users\\tester' },
    path,
  });
  await openCodexConfig();
  configExists = false;
  await openCodexConfig();
  assert.deepEqual(opened, [
    path.join('C:\\Users\\tester', '.codex', 'config.toml'),
    path.join('C:\\Users\\tester', '.codex'),
  ]);
});

test('environment shortcut opens the Windows editor without passing the token', () => {
  const launches = [];
  const child = { on: () => child, unref: () => {} };
  const { openEnvironmentVariables } = load({
    child_process: { spawn: (...args) => { launches.push(args); return child; } },
    electron: { shell: {} },
    fs: { existsSync: () => true },
    os: { homedir: () => 'C:\\Users\\tester', platform: () => 'win32' },
    path,
  });
  openEnvironmentVariables(() => {});
  assert.equal(launches.length, 1);
  assert.equal(launches[0][0], 'rundll32.exe');
  assert.deepEqual(launches[0][1], ['sysdm.cpl,EditEnvironmentVariables']);
  assert.equal(JSON.stringify(launches).includes('OBSIDIAN_CONTEXT_SCOPE_TOKEN'), false);
});

test('environment shortcut is unavailable outside Windows', () => {
  let launched = false;
  const { openEnvironmentVariables } = load({
    child_process: { spawn: () => { launched = true; } },
    electron: { shell: {} },
    fs: { existsSync: () => true },
    os: { homedir: () => '/home/tester', platform: () => 'linux' },
    path,
  });
  assert.throws(() => openEnvironmentVariables(() => {}), /Windows/);
  assert.equal(launched, false);
});
