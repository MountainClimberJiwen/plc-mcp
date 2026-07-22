"""
汇川 InoProShop 适配器

通过 InoProShop_LIMIT_MCP（基于 CODESYS Script Engine）
实现程序块源码的读取、写入和编译。

技术栈：
- 通信方式：MCP stdio（启动 Node.js bundle）
- 支持类型：Program / FunctionBlock / Function
- 支持语言：ST（结构化文本）

已知限制（受限于 InoProShop_LIMIT_MCP / SP11 脚本 API）：
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
from .inoproshop_mcp_client import InoProShopMCPClient
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


class InoProShopAdapter(PLCAdapter):
    """
    汇川 InoProShop 适配器

    通过 InoProShop_LIMIT_MCP 与 InoProShop 通信，
    将 POU 映射为虚拟的 PLC 块供 AI 操作。
    """

    def __init__(
        self,
        project_path: str,
        bundle_path: str,
        codesys_path: str,
        profile: str = "InoProShop(V1.9.0.1)",
        workspace: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """
        初始化适配器

        Args:
            project_path: InoProShop 工程文件 .project 的完整路径
            bundle_path: InoProShop_LIMIT_MCP 的 bundle.min.js 路径
            codesys_path: InoProShop.exe 完整路径
            profile: CODESYS profile 名称
            workspace: 工程工作目录，默认取 project_path 所在目录
            timeout: MCP 请求超时（秒）
        """
        self.project_path = os.path.abspath(project_path)
        self.bundle_path = os.path.abspath(bundle_path)
        self.codesys_path = os.path.abspath(codesys_path)
        self.profile = profile
        self.workspace = os.path.abspath(workspace or os.path.dirname(self.project_path))
        self.timeout = timeout

        self._client: Optional[InoProShopMCPClient] = None
        self._structure: Optional[Dict[str, Any]] = None

    # === PLCAdapter 接口实现 ===

    @property
    def brand(self) -> str:
        return "inoproshop"

    def connect(self) -> bool:
        """启动 InoProShop_LIMIT_MCP 并打开工程"""
        if self._client is not None:
            return True

        args = [
            self.bundle_path,
            "--codesys-path", self.codesys_path,
            "--codesys-profile", self.profile,
            "--workspace", self.workspace,
        ]

        self._client = InoProShopMCPClient(
            command="node",
            args=args,
            timeout=self.timeout,
        )

        if os.path.exists(self.project_path):
            self._client.call_tool("open_project", {"project_path": self.project_path})
        else:
            # 尝试自动创建基础工程
            try:
                project_name = Path(self.project_path).stem
                self._client.call_tool(
                    "create_project",
                    {
                        "name": project_name,
                        "directory": self.workspace,
                        "template": "standard",
                    },
                )
            except Exception as e:
                raise FileNotFoundError(
                    f"项目 {self.project_path} 不存在，且自动创建失败。"
                    f"请先在 InoProShop 中创建基础工程。"
                ) from e

        return True

    def disconnect(self) -> None:
        """关闭 InoProShop_LIMIT_MCP 子进程"""
        if self._client:
            self._client.close()
            self._client = None

    def read_block(self, block_name: str) -> PLCBlock:
        """读取指定 POU 的源码"""
        if not self._client:
            raise RuntimeError("适配器未连接")

        structure = self._get_structure()
        node = _find_node(structure, block_name)
        if node is None:
            raise FileNotFoundError(
                f"块 '{block_name}' 不存在。可用块: {self.list_blocks()}"
            )

        code_data = self._client.call_tool("get_pou_code", {"pou_path": block_name})
        if not isinstance(code_data, dict):
            raise RuntimeError(f"get_pou_code 返回格式异常: {code_data!r}")

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
        if not self._client:
            raise RuntimeError("适配器未连接")

        # 如果块不存在，先创建
        if not self.block_exists(block.name):
            block_type = block.block_type or "Program"
            # 反向映射回 CODESYS 类型
            codesys_type = "Program" if block_type == "PRG" else (
                "FunctionBlock" if block_type == "FB" else (
                    "Function" if block_type == "FC" else block_type
                )
            )
            self._client.call_tool(
                "create_pou",
                {"name": block.name, "type": codesys_type},
            )
            self._invalidate_structure()

        declaration, implementation = _split_source_code(block.source_code or "")

        self._client.call_tool(
            "set_pou_code",
            {
                "pou_path": block.name,
                "declaration": declaration,
                "implementation": implementation,
            },
        )
        self._client.call_tool("save_project", {})
        return True

    def list_blocks(self) -> List[str]:
        """列出所有 POU 名称"""
        if not self._client:
            raise RuntimeError("适配器未连接")
        structure = self._get_structure()
        return _extract_pou_names(structure)

    def compile(self) -> Dict[str, Any]:
        """编译项目并返回结果"""
        if not self._client:
            raise RuntimeError("适配器未连接")

        result = self._client.call_tool("compile_project", {})
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                result = {"message": result}

        return {
            "success": result.get("success", False) if isinstance(result, dict) else False,
            "warnings": result.get("warnings", 0) if isinstance(result, dict) else 0,
            "errors": result.get("errors", 0) if isinstance(result, dict) else 0,
            "message": result.get("message", "") if isinstance(result, dict) else str(result),
        }

    # === 内部辅助 ===

    def _get_structure(self) -> Dict[str, Any]:
        """获取并缓存项目结构树"""
        if self._structure is None:
            structure = self._client.call_tool("get_project_structure", {})
            if not isinstance(structure, dict):
                # 某些版本可能返回列表，包装成根节点
                structure = {"name": "root", "type": "Project", "children": structure if isinstance(structure, list) else []}
            self._structure = structure
        return self._structure

    def _invalidate_structure(self) -> None:
        """项目结构缓存失效"""
        self._structure = None

    def is_connected(self) -> bool:
        return self._client is not None

    def __repr__(self) -> str:
        status = "connected" if self.is_connected() else "disconnected"
        return (
            f"InoProShopAdapter("
            f"project={self.project_path}, "
            f"profile={self.profile}, "
            f"status={status}, "
            f"blocks={len(self.list_blocks()) if self.is_connected() else 0}"
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
