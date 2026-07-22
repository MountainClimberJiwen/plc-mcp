"""
汇川 InoProShop 适配器单元测试

测试范围：
- MockInoProShopAdapter（无需真实 IDE）
- InoProShopAdapter 的源码拆分 / 结构树解析辅助函数
- InoProShopMCPClient 的 JSON-RPC 通信（使用伪造子进程）
- PLCVirtualFS + MockInoProShopAdapter 集成

运行方式：
    pytest tests/test_inoproshop_adapter.py -v
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from plc_vfs.adapters.inoproshop import (
    InoProShopAdapter,
    MockInoProShopAdapter,
    _extract_pou_names,
    _find_node,
    _split_source_code,
)
from plc_vfs.adapters.inoproshop_mcp_client import InoProShopMCPClient
from plc_vfs.core import PLCBlock, PLCVirtualFS


# === 辅助函数测试 ===

class TestSourceCodeHelpers:
    """测试源码拆分和结构树解析"""

    def test_split_source_code_with_vars(self):
        code = """PROGRAM Main
VAR
    counter : INT;
END_VAR

counter := counter + 1;
END_PROGRAM
"""
        decl, impl = _split_source_code(code)
        assert "PROGRAM Main" in decl
        assert "VAR" in decl
        assert "END_VAR" in decl
        assert "counter := counter + 1;" in impl

    def test_split_source_code_no_vars(self):
        code = """PROGRAM Main

counter := counter + 1;
END_PROGRAM
"""
        decl, impl = _split_source_code(code)
        assert decl == ""
        assert "counter := counter + 1;" in impl

    def test_extract_pou_names(self):
        structure = {
            "name": "Application",
            "type": "Application",
            "children": [
                {"name": "Main", "type": "Program"},
                {"name": "Motor_FB", "type": "FunctionBlock"},
                {"name": "Add", "type": "Function"},
                {"name": "GlobalVars", "type": "GVL"},
            ],
        }
        names = _extract_pou_names(structure)
        assert "Main" in names
        assert "Motor_FB" in names
        assert "Add" in names
        assert "GlobalVars" not in names

    def test_find_node(self):
        structure = {
            "name": "Application",
            "type": "Application",
            "children": [
                {"name": "Main", "type": "Program"},
                {
                    "name": "Folder",
                    "type": "Folder",
                    "children": [
                        {"name": "Motor_FB", "type": "FunctionBlock"},
                    ],
                },
            ],
        }
        node = _find_node(structure, "Motor_FB")
        assert node is not None
        assert node["type"] == "FunctionBlock"


# === Mock 适配器测试 ===

class TestMockInoProShopAdapter:
    """测试 MockInoProShopAdapter"""

    @pytest.fixture
    def adapter(self):
        adapter = MockInoProShopAdapter()
        adapter.connect()
        yield adapter
        adapter.disconnect()

    def test_connect(self, adapter):
        assert adapter.is_connected()

    def test_brand(self, adapter):
        assert adapter.brand == "inoproshop"

    def test_list_blocks(self, adapter):
        blocks = adapter.list_blocks()
        assert "Main" in blocks
        assert "Motor_FB" in blocks

    def test_read_block(self, adapter):
        block = adapter.read_block("Main")
        assert isinstance(block, PLCBlock)
        assert block.name == "Main"
        assert "PROGRAM Main" in block.source_code

    def test_write_block(self, adapter):
        new_code = """PROGRAM Main
VAR
    counter : INT;
END_VAR

counter := 100;
END_PROGRAM
"""
        block = PLCBlock(name="Main", source_code=new_code)
        assert adapter.write_block(block) is True

        read_back = adapter.read_block("Main")
        assert "counter := 100;" in read_back.source_code

    def test_compile(self, adapter):
        result = adapter.compile()
        assert result["success"] is True
        assert result["errors"] == 0


# === VFS 集成测试 ===

class TestVFSIntegration:
    """测试 PLCVirtualFS + MockInoProShopAdapter"""

    @pytest.fixture
    def vfs(self):
        adapter = MockInoProShopAdapter()
        adapter.connect()
        return PLCVirtualFS(adapter)

    def test_ls(self, vfs):
        blocks = vfs.ls("/devices/PLC_1/blocks")
        assert "Main.scl" in blocks
        assert "Motor_FB.scl" in blocks

    def test_cat(self, vfs):
        content = vfs.cat("/devices/PLC_1/blocks/Main.scl")
        assert "PROGRAM Main" in content

    def test_write_and_read(self, vfs):
        new_code = """PROGRAM Main
VAR
    counter : INT;
END_VAR

counter := 999;
END_PROGRAM
"""
        vfs.echo(new_code, "/devices/PLC_1/blocks/Main.scl")
        content = vfs.cat("/devices/PLC_1/blocks/Main.scl")
        assert "counter := 999;" in content

    def test_grep(self, vfs):
        matches = vfs.grep("counter", "/devices/PLC_1/blocks/Main.scl")
        assert len(matches) > 0

    def test_diff(self, vfs):
        diff = vfs.diff(
            "/devices/PLC_1/blocks/Main.scl",
            "/devices/PLC_1/blocks/Motor_FB.scl",
        )
        assert "---" in diff or "+++" in diff


# === MCP 客户端测试 ===

@pytest.fixture
def fake_mcp_server():
    """创建一个伪造的 MCP 子进程脚本，并返回其路径"""
    script = '''
import json
import sys

def send(obj):
    sys.stdout.write(json.dumps(obj) + "\\n")
    sys.stdout.flush()

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue

    method = msg.get("method")
    msg_id = msg.get("id")

    if method == "initialize":
        send({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "fake", "version": "1.0"},
            },
        })
    elif method == "tools/call":
        name = msg["params"]["name"]
        if name == "get_pou_code":
            text = json.dumps({
                "declaration": "VAR_INPUT\\n  x : INT;\\nEND_VAR",
                "implementation": "x := 1;",
            })
            send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": text}]},
            })
        else:
            send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": "ok"}]},
            })
'''
    fd, path = tempfile.mkstemp(suffix=".py")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(script)
    yield path
    os.unlink(path)


class TestInoProShopMCPClient:
    """测试 InoProShopMCPClient 的 JSON-RPC 通信"""

    def test_call_tool_returns_parsed_json(self, fake_mcp_server):
        client = InoProShopMCPClient(
            command=sys.executable,
            args=[fake_mcp_server],
            timeout=10.0,
        )
        try:
            result = client.call_tool("get_pou_code", {"pou_path": "Main"})
            assert isinstance(result, dict)
            assert "declaration" in result
            assert "implementation" in result
        finally:
            client.close()

    def test_call_tool_returns_text(self, fake_mcp_server):
        client = InoProShopMCPClient(
            command=sys.executable,
            args=[fake_mcp_server],
            timeout=10.0,
        )
        try:
            result = client.call_tool("compile_project", {})
            assert result == "ok"
        finally:
            client.close()


# === 运行入口 ===

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
