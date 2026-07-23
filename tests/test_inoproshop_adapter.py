"""
汇川 InoProShop 适配器单元测试

测试范围：
- MockInoProShopAdapter（无需真实 IDE）
- InoProShopAdapter 的源码拆分 / 结构树解析辅助函数
- PLCVirtualFS + MockInoProShopAdapter 集成
- InoProShopScriptRunner 的解析逻辑（使用伪造 CODESYS 可执行文件）

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
    _find_standard_template,
    _split_source_code,
)
from plc_vfs.adapters.inoproshop_script_runner import InoProShopScriptRunner
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


class TestTemplateFinder:
    """测试标准模板查找"""

    def test_find_standard_template_returns_existing_file(self):
        # 用一个真实存在的文件模拟模板
        fd, path = tempfile.mkstemp(suffix=".project")
        os.close(fd)
        try:
            exe_dir = os.path.dirname(path)
            template_dir = os.path.join(exe_dir, "Templates")
            os.makedirs(template_dir, exist_ok=True)
            template_path = os.path.join(template_dir, "Standard.project")
            os.rename(path, template_path)

            result = _find_standard_template(
                os.path.join(exe_dir, "InoProShop.exe"),
                "InoProShop(V1.9.0.1)",
            )
            assert result == template_path
        finally:
            try:
                os.unlink(template_path)
            except Exception:
                pass
            try:
                os.rmdir(template_dir)
            except Exception:
                pass

    def test_find_standard_template_not_found(self):
        fd, path = tempfile.mkstemp(suffix=".project")
        os.close(fd)
        os.unlink(path)
        result = _find_standard_template(
            os.path.join(os.path.dirname(path), "InoProShop.exe"),
            "InoProShop(V1.9.0.1)",
        )
        assert result is None


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


# === ScriptRunner 测试 ===

@pytest.fixture
def fake_codesys_exe():
    """创建一个伪造的 CODESYS 可执行脚本，模拟 --runscript 行为。"""
    py_script = r'''
import sys
import os

# 模拟 InoProShop.exe 参数解析：--profile=... --runscript=<py>
runscript = None
for arg in sys.argv[1:]:
    if arg.startswith("--runscript="):
        runscript = arg[len("--runscript="):]

if runscript is None:
    sys.stderr.write("missing --runscript\n")
    sys.exit(2)

# 从脚本里提取 _RESULT_FILE 路径
result_file = None
with open(runscript, "r", encoding="utf-8") as f:
    for line in f:
        if "_RESULT_FILE =" in line:
            line = line.strip()
            quote = "'" if "r'" in line else '"'
            start = line.find(quote)
            end = line.rfind(quote)
            if start != -1 and end != -1 and end > start:
                result_file = line[start+1:end]
            break

if result_file is None:
    sys.stderr.write("could not find _RESULT_FILE\n")
    sys.exit(3)

class FakeProject:
    def __init__(self):
        self.path = r"C:\fake\test.project"
        self.name = "test"
    def save(self):
        pass

class FakeProjects:
    def __init__(self):
        self._primary = FakeProject()
    @property
    def primary(self):
        return self._primary
    def open(self, path):
        self._primary.path = path
        return self._primary

# 让脚本里的 "import scriptengine as _se_hdr" 能成功
fake_se = type("FakeScriptEngine", (), {"projects": FakeProjects()})
sys.modules["scriptengine"] = fake_se()

import json as _json

globs = {
    "json": _json,
    "rlog": lambda s: open(result_file, "ab").write((str(s)+"\n").encode("utf-8")),
}

with open(runscript, "r", encoding="utf-8") as f:
    source = f.read()

exec(source, globs)

# exec 完成后，如果脚本没写标记，默认加一个成功标记
with open(result_file, "r", encoding="utf-8") as f:
    content = f.read()
if "SCRIPT_SUCCESS" not in content and "SCRIPT_ERROR" not in content:
    with open(result_file, "ab") as f:
        f.write(b"SCRIPT_SUCCESS: fake\n")
'''

    tmp_dir = tempfile.mkdtemp()
    py_path = os.path.join(tmp_dir, "fake_codesys.py")
    exe_path = os.path.join(tmp_dir, "fake_codesys")

    with open(py_path, "w", encoding="utf-8") as f:
        f.write(py_script)

    # 用 shell 包装器调用 python 解释器，模拟真实可执行文件
    with open(exe_path, "w", encoding="utf-8") as f:
        f.write(f'#!/bin/sh\nexec "{sys.executable}" "{py_path}" "$@"\n')

    os.chmod(exe_path, 0o755)

    yield exe_path

    # 清理
    try:
        os.unlink(py_path)
    except Exception:
        pass
    try:
        os.unlink(exe_path)
    except Exception:
        pass
    try:
        os.rmdir(tmp_dir)
    except Exception:
        pass


class TestInoProShopScriptRunner:
    """测试 InoProShopScriptRunner 与伪造 CODESYS 的交互。"""

    def test_run_open_project(self, fake_codesys_exe):
        runner = InoProShopScriptRunner(
            codesys_path=fake_codesys_exe,
            profile="TestProfile",
            timeout=10.0,
        )
        from plc_vfs.adapters import inoproshop_scripts as scripts

        result = runner.run_script("open_project", scripts.build_open_project(r"C:\fake\test.project"))
        assert result["success"] is True
        assert "SCRIPT_SUCCESS" in result["output"]

    def test_run_get_project_structure(self, fake_codesys_exe):
        runner = InoProShopScriptRunner(
            codesys_path=fake_codesys_exe,
            profile="TestProfile",
            timeout=10.0,
        )
        from plc_vfs.adapters import inoproshop_scripts as scripts

        result = runner.run_script(
            "get_project_structure",
            scripts.build_get_project_structure(),
        )
        assert result["success"] is True
        assert "SCRIPT_SUCCESS" in result["output"]

    def test_transformed_print_goes_to_result_file(self, fake_codesys_exe):
        runner = InoProShopScriptRunner(
            codesys_path=fake_codesys_exe,
            profile="TestProfile",
            timeout=10.0,
        )
        # 业务脚本里用 print 而不是 rlog，runner 应该把它转成 rlog
        result = runner.run_script(
            "print_test",
            'print("SCRIPT_SUCCESS: print_test")\nsys.exit(0)\n',
        )
        assert result["success"] is True
        assert "print_test" in result["output"]

    def test_missing_executable_raises(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        os.unlink(path)
        with pytest.raises(FileNotFoundError):
            InoProShopScriptRunner(codesys_path=path, profile="TestProfile")


# === 运行入口 ===

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
