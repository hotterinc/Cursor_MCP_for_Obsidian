from pathlib import Path

from starlette.testclient import TestClient

from obsidian_context_mcp.core.vault_context import get_vault_context
from obsidian_context_mcp.shared.types import AccessScope
from obsidian_context_mcp.vault_server.http_app import create_http_app


def test_admin_capability_and_masked_scope_export(tmp_path: Path) -> None:
    vault = tmp_path / 'vault'
    vault.mkdir()
    ctx = get_vault_context(str(vault), data_dir=tmp_path / 'data')
    ctx.scope_store.upsert(AccessScope(id='s', name='Notes', token='scope-secret'))
    (ctx.data_dir / 'runtime.json').write_text('{"port": 12345}', encoding='utf-8')
    with TestClient(create_http_app(ctx, admin_token='admin-secret')) as client:
        assert client.get('/api/v1/scopes').status_code == 401
        assert client.get('/api/v1/scopes', headers={'Authorization': 'Bearer scope-secret'}).status_code == 401
        headers = {'Authorization': 'Bearer admin-secret'}
        scopes = client.get('/api/v1/scopes', headers=headers).json()['scopes']
        assert 'token' not in scopes[0]
        updated = client.post('/api/v1/scopes', headers=headers, json={'id': 's', 'name': 'Updated', 'token': 'stale'})
        assert updated.status_code == 200
        assert ctx.scope_store.get_by_id('s').token == 'scope-secret'
        exported = client.get('/api/v1/scopes/s/codex-config', headers=headers).json()
        assert 'http://127.0.0.1:12345/mcp' in exported['config']
        assert 'bearer_token_env_var' in exported['config']
        assert 'scope-secret' not in exported['config']
        assert client.get('/api/v1/scopes/s/token', headers=headers).json()['token'] == 'scope-secret'
        assert client.post('/mcp').status_code == 401

def test_streamable_http_tools_and_revocation(tmp_path: Path) -> None:
    vault = tmp_path / 'vault'
    vault.mkdir()
    (vault / 'Allowed.md').write_text('hello', encoding='utf-8')
    ctx = get_vault_context(str(vault), data_dir=tmp_path / 'data')
    scope = AccessScope(id='s', name='Notes', token='scope-secret')
    ctx.scope_store.upsert(scope)
    headers = {'Authorization': 'Bearer scope-secret', 'Accept': 'application/json, text/event-stream', 'Host': '127.0.0.1'}
    with TestClient(create_http_app(ctx, admin_token='admin-secret')) as client:
        def rpc(method, params, number=1):
            response = client.post('/mcp', headers=headers, json={'jsonrpc': '2.0', 'id': number, 'method': method, 'params': params})
            assert response.status_code == 200, response.text
            return response.json()['result']
        result = rpc('initialize', {'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}})
        assert result['serverInfo']['name'] == 'obsidian-context-vault'
        tools = rpc('tools/list', {})['tools']
        assert any(tool['name'] == 'scope_get_info' for tool in tools)
        result = rpc('tools/call', {'name': 'scope_get_info', 'arguments': {}})
        assert not result.get('isError')
        scope.include = []
        ctx.scope_store.upsert(scope)
        result = rpc('tools/call', {'name': 'docs_read_note', 'arguments': {'relativePath': 'Allowed.md'}})
        assert result['isError']
        ctx.scope_store.regenerate_token('s')
        assert client.post('/mcp', headers=headers).status_code == 401
