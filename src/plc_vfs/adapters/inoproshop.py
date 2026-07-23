"""
汇川 InoProShop 适配器

通过 CODESYS Script Engine（IronPython）直接驱动 InoProShop，
实现程序块源码的读取、写入和编译。

技术栈：
- 通信方式：Python 生成 IronPython 脚本，启动 InoProShop.exe --runscript 执行
- 支持类型：Program / FunctionBlock / Function
- 支持语言：ST（结构化文本）

已知限制（受限于 SP11 脚本 API）：
- 无法自动向 Task 添加/删除 POU 调用
- 无法做 IO 通道变量映射
- 无法做 EtherCAT PDO 映射配置
- 新建 POU 后可能需要手动在 InoProShop 中挂到 Task 上
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import PLCAdapter
from .inoproshop_script_runner import InoProShopScriptRunner
from ..core import PLCBlock


# CODESYS 项目结构中的 POU 类型
_POU_TYPES = {"program", "functionblock", "function", "pou"}

# CODESYS 类型 -> PLCBlock.block_type 映射
_TYPE_MAP = {
    "program": "PRG",
    "functionblock": "FB",
    "function": "FC",
    "pou": "POU",
}

# PLCBlock.block_type -> CODESYS POU 类型反向映射
_REVERSE_TYPE_MAP = {
    "PRG": "Program",
    "FB": "FunctionBlock",
    "FC": "Function",
    "POU": "POU",
}


def _split_source_code(code: str) -> Tuple[str, str]:
    """
    把完整的 ST 源码拆分为 declaration / implementation

    CODESYS set_pou_code 需要分开传入：
    - declaration: VAR_INPUT / VAR_OUTPUT / VAR 等声明段
    - implementation: 实际 ST 执行代码

    这里按最后一个 END_VAR 分界。如果源码没有声明段，则 declaration 为空。
    """
    matches = list(re.finditer(r"(?i)\bEND_VAR\b", code))
    if not matches:
        return "", code.strip()

    end_pos = matches[-1].end()
    declaration = code[:end_pos].strip()
    implementation = code[end_pos:].strip()
    return declaration, implementation


def _extract_pou_names(structure: Any) -> List[str]:
    """从 get_project_structure 返回的树中递归提取 POU 名称"""
    names: List[str] = []

    def walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        node_type = str(node.get("type", "")).lower()
        if node_type in _POU_TYPES:
            name = node.get("name")
            if name:
                names.append(str(name))
        for child in node.get("children", []):
            walk(child)

    if isinstance(structure, dict):
        walk(structure)
    elif isinstance(structure, list):
        for item in structure:
            walk(item)

    return names


def _find_node(structure: Any, name: str) -> Optional[Dict[str, Any]]:
    """在项目结构树中按名称查找节点"""
    result: Optional[Dict[str, Any]] = None

    def walk(node: Any) -> None:
        nonlocal result
        if result is not None:
            return
        if not isinstance(node, dict):
            return
        if str(node.get("name", "")) == name:
            result = node
            return
        for child in node.get("children", []):
            walk(child)

    if isinstance(structure, dict):
        walk(structure)
    elif isinstance(structure, list):
        for item in structure:
            walk(item)

    return result


def _find_standard_template(codesys_path: str, profile: str) -> Optional[str]:
    """
    尝试定位 CODESYS Standard.project 模板文件。

    搜索顺序：
    1. 可执行文件同级 Templates/Standard.project
    2. ProgramData/CODESYS/CODESYS/<profile>/Templates/Standard.project
    3. ProgramData/CODESYS/Templates/Standard.project
    """
    candidates: List[str] = []

    exe_dir = os.path.dirname(os.path.abspath(codesys_path))
    candidates.append(os.path.join(exe_dir, "Templates", "Standard.project"))

    all_users = os.environ.get("ALLUSERSPROFILE") or os.environ.get("ProgramData") or r"C:\ProgramData"
    candidates.append(
        os.path.join(all_users, "CODESYS", "CODESYS", profile, "Templates", "Standard.project")
    )
    candidates.append(os.path.join(all_users, "CODESYS", "Templates", "Standard.project"))

    for path in candidates:
        normalized = os.path.normpath(path)
        if os.path.exists(normalized):
            return normalized
    return None


class InoProShopAdapter(PLCAdapter):
    """
    汇川 InoProShop 适配器

    通过 Python 原生生成 IronPython 脚本并驱动 InoProShop/CODESYS，
    将 POU 映射为虚拟的 PLC 块供 AI 操作。
    """

    def __init__(
        self,
        project_path: str,
        codesys_path: str,
        profile: str = "InoProShop(V1.9.0.1)",
        workspace: Optional[str] = None,
        timeout: float = 300.0,
    ):
        """
        初始化适配器

        Args:
            project_path: InoProShop 工程文件 .project 的完整路径
            codesys_path: InoProShop.exe 完整路径
            profile: CODESYS profile 名称
            workspace: 工程工作目录，默认取 project_path 所在目录
            timeout: 脚本执行超时（秒）
        """
        self.project_path = os.path.abspath(project_path)
        self.codesys_path = os.path.abspath(codesys_path)
        self.profile = profile
        self.workspace = os.path.abspath(workspace or os.path.dirname(self.project_path))
        self.timeout = timeout

        self._runner: Optional[InoProShopScriptRunner] = None
        self._structure: Optional[Dict[str, Any]] = None

    # === PLCAdapter 接口实现 ===

    @property
    def brand(self) -> str:
        return "inoproshop"

    def connect(self) -> bool:
        """初始化脚本运行器并确保工程已打开。"""
        if self._runner is not None:
            return True

        self._runner = InoProShopScriptRunner(
            codesys_path=self.codesys_path,
            profile=self.profile,
            workspace=self.workspace,
            timeout=self.timeout,
        )

        if os.path.exists(self.project_path):
            result = self._runner.open_project(self.project_path)
            if not result.get("success", False):
                raise RuntimeError(
                    f"打开项目失败: {result.get('output', 'unknown error')}"
                )
        else:
            # 尝试自动创建基础工程
            try:
                template = _find_standard_template(self.codesys_path, self.profile)
                if template is None:
                    raise FileNotFoundError(
                        "找不到 Standard.project 模板，无法自动创建项目。"
                    )
                result = self._runner.create_project(self.project_path, template)
                if not result.get("success", False):
                    raise RuntimeError(
                        f"创建项目失败: {result.get('output', 'unknown error')}"
                    )
            except Exception as e:
                raise FileNotFoundError(
                    f"项目 {self.project_path} 不存在，且自动创建失败。"
                    f"请先在 InoProShop 中创建基础工程。"
                ) from e

        return True

    def disconnect(self) -> None:
        """释放脚本运行器（CODESYS 子进程会在脚本结束后自动退出）。"""
        self._runner = None
        self._structure = None

    def read_block(self, block_name: str) -> PLCBlock:
        """读取指定 POU 的源码"""
        if not self._runner:
            raise RuntimeError("适配器未连接")

        structure = self._get_structure()
        node = _find_node(structure, block_name)
        if node is None:
            raise FileNotFoundError(
                f"块 '{block_name}' 不存在。可用块: {self.list_blocks()}"
            )

        result = self._runner.get_pou_code(block_name)
        if not result.get("success", False):
            raise RuntimeError(
                f"get_pou_code 失败: {result.get('output', 'unknown error')}"
            )

        code_data = self._try_parse_json(result.get("output", ""))
        if not isinstance(code_data, dict):
            raise RuntimeError(f"get_pou_code 返回格式异常: {result!r}")

        declaration = code_data.get("declaration", "")
        implementation = code_data.get("implementation", "")

        source_code = declaration
        if implementation:
            source_code = f"{declaration}\n\n{implementation}" if declaration else implementation

        block_type = _TYPE_MAP.get(str(node.get("type", "")).lower(), "POU")

        return PLCBlock(
            name=block_name,
            block_type=block_type,
            language="ST",
            source_code=source_code.strip(),
            metadata={
                "brand": "inoproshop",
                "profile": self.profile,
                "project_path": self.project_path,
                "node_type": node.get("type"),
                "declaration": declaration,
                "implementation": implementation,
            },
        )

    def write_block(self, block: PLCBlock) -> bool:
        """写入 POU 源码并保存"""
        if not self._runner:
            raise RuntimeError("适配器未连接")

        # 如果块不存在，先创建
        if not self.block_exists(block.name):
            codesys_type = _REVERSE_TYPE_MAP.get(
                block.block_type or "PRG", "Program"
            )
            result = self._runner.create_pou(block.name, codesys_type)
            if not result.get("success", False):
                raise RuntimeError(
                    f"创建 POU 失败: {result.get('output', 'unknown error')}"
                )
            self._invalidate_structure()

        declaration, implementation = _split_source_code(block.source_code or "")

        result = self._runner.set_pou_code(block.name, declaration, implementation)
        if not result.get("success", False):
            raise RuntimeError(
                f"写入 POU 失败: {result.get('output', 'unknown error')}"
            )

        save_result = self._runner.save_project()
        if not save_result.get("success", False):
            raise RuntimeError(
                f"保存项目失败: {save_result.get('output', 'unknown error')}"
            )

        return True

    def list_blocks(self) -> List[str]:
        """列出所有 POU 名称"""
        if not self._runner:
            raise RuntimeError("适配器未连接")
        structure = self._get_structure()
        return _extract_pou_names(structure)

    def compile(self) -> Dict[str, Any]:
        """编译项目并返回结果"""
        if not self._runner:
            raise RuntimeError("适配器未连接")

        result = self._runner.compile_project()
        if not result.get("success", False):
            # 编译返回错误时也把 output 解析成 dict
            parsed = self._try_parse_json(result.get("output", ""))
            if isinstance(parsed, dict):
                parsed["success"] = False
                return parsed
            return {
                "success": False,
                "warnings": 0,
                "errors": 1,
                "message": result.get("output", "compile failed"),
            }

        parsed = self._try_parse_json(result.get("output", ""))
        if isinstance(parsed, dict):
            return parsed

        return {
            "success": True,
            "warnings": 0,
            "errors": 0,
            "message": result.get("output", ""),
        }

    # === 内部辅助 ===

    def _get_structure(self) -> Dict[str, Any]:
        """获取并缓存项目结构树"""
        if self._structure is None:
            result = self._runner.get_project_structure()
            if not result.get("success", False):
                raise RuntimeError(
                    f"获取项目结构失败: {result.get('output', 'unknown error')}"
                )

            structure = self._try_parse_json(result.get("output", ""))
            if not isinstance(structure, dict):
                # 某些版本可能返回列表，包装成根节点
                structure = {
                    "name": "root",
                    "type": "Project",
                    "children": structure if isinstance(structure, list) else [],
                }
            self._structure = structure
        return self._structure

    def _invalidate_structure(self) -> None:
        """项目结构缓存失效"""
        self._structure = None

    def _try_parse_json(self, text: str) -> Any:
        """尝试从文本中解析 JSON 对象或数组。"""
        stripped = text.strip()
        # 找到第一个 { 或 [ 位置
        start_idx = -1
        for ch in ("{", "["):
            idx = stripped.find(ch)
            if idx != -1 and (start_idx == -1 or idx < start_idx):
                start_idx = idx
        if start_idx == -1:
            return None
        candidate = stripped[start_idx:]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None

    def is_connected(self) -> bool:
        return self._runner is not None

    def __repr__(self) -> str:
        status = "connected" if self.is_connected() else "disconnected"
        block_count = 0
        if self.is_connected():
            try:
                block_count = len(self.list_blocks())
            except Exception:
                pass
        return (
            f"InoProShopAdapter("
            f"project={self.project_path}, "
            f"profile={self.profile}, "
            f"status={status}, "
            f"blocks={block_count}"
            f")"
        )


class MockInoProShopAdapter(PLCAdapter):
    """
    Mock InoProShop 适配器

    用于无 InoProShop / 无 Windows 环境的单元测试。
    """

    def __init__(self, blocks: Optional[Dict[str, str]] = None):
        self._blocks: Dict[str, PLCBlock] = {}
        default_sources = {
            "Main": """PROGRAM Main
VAR
    counter : INT;
END_VAR

counter := counter + 1;
END_PROGRAM
""",
            "Motor_FB": """FUNCTION_BLOCK Motor_FB
VAR_INPUT
    Start : BOOL;
END_VAR
VAR_OUTPUT
    Running : BOOL;
END_VAR

Running := Start;
END_FUNCTION_BLOCK
""",
        }

        sources = blocks or default_sources
        for name, source in sources.items():
            block_type = "PRG" if name == "Main" else "FB"
            self._blocks[name] = PLCBlock(
                name=name,
                block_type=block_type,
                language="ST",
                source_code=source.strip(),
                metadata={"brand": "inoproshop"},
            )

        self._connected = False

    @property
    def brand(self) -> str:
        return "inoproshop"

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def read_block(self, block_name: str) -> PLCBlock:
        if block_name not in self._blocks:
            raise FileNotFoundError(f"块 '{block_name}' 不存在")
        return self._blocks[block_name]

    def write_block(self, block: PLCBlock) -> bool:
        self._blocks[block.name] = block
        return True

    def list_blocks(self) -> List[str]:
        return list(self._blocks.keys())

    def compile(self) -> Dict[str, Any]:
        return {
            "success": True,
            "warnings": 0,
            "errors": 0,
            "message": "Mock compile success",
        }

    def is_connected(self) -> bool:
        return self._connected
