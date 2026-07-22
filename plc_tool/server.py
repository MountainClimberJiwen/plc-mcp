"""
PLC Universal MCP Server

通过 VFS 把不同品牌 PLC 项目映射为统一文件路径，
AI 可以通过 MCP Tools 直接读写程序块、编译项目。

支持品牌（由环境变量 PLC_MCP_BRAND 控制）：
- inoproshop：汇川 InoProShop（基于 InoProShop_LIMIT_MCP）
- inovance：汇川 AM600/AC800（基于 Modbus TCP）
- siemens：西门子 TIA Portal（基于 TIA Openness）
- mock：Mock InoProShop（用于测试）
"""

import json
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

# 确保能导入 src/plc_vfs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from plc_vfs.core import PLCVirtualFS
from plc_vfs.adapters import (
    InoProShopAdapter,
    InovanceAM600Adapter,
    MockInoProShopAdapter,
)
from plc_vfs.adapters.base import PLCAdapter

mcp = FastMCP("plc-mcp")

# 全局 VFS 实例，在 main() 中初始化
vfs: PLCVirtualFS = None  # type: ignore[assignment]


def _create_adapter() -> PLCAdapter:
    """根据环境变量创建对应品牌的适配器"""
    brand = os.getenv("PLC_MCP_BRAND", "mock").lower()

    if brand == "inoproshop":
        required = [
            "INOPROSHOP_PROJECT_PATH",
            "INOPROSHOP_BUNDLE_PATH",
            "INOPROSHOP_CODESYS_PATH",
        ]
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise RuntimeError(
                f"InoProShop 适配器缺少环境变量: {', '.join(missing)}"
            )
        return InoProShopAdapter(
            project_path=os.environ["INOPROSHOP_PROJECT_PATH"],
            bundle_path=os.environ["INOPROSHOP_BUNDLE_PATH"],
            codesys_path=os.environ["INOPROSHOP_CODESYS_PATH"],
            profile=os.getenv("INOPROSHOP_PROFILE", "InoProShop(V1.9.0.1)"),
        )

    if brand == "inovance":
        return InovanceAM600Adapter(
            host=os.getenv("INOVANCE_PLC_HOST", "192.168.1.10"),
            port=int(os.getenv("INOVANCE_PLC_PORT", "502")),
            block_map_path=os.getenv(
                "INOVANCE_BLOCK_MAP", "config/inovance_blocks.json"
            ),
        )

    if brand == "siemens":
        from plc_vfs.core import SiemensTIAAdapter

        project_path = os.environ.get("TIA_PROJECT_PATH")
        if not project_path:
            raise RuntimeError("西门子适配器需要环境变量 TIA_PROJECT_PATH")
        return SiemensTIAAdapter(project_path=project_path)

    # 默认 mock，用于本地测试
    return MockInoProShopAdapter()


@mcp.tool()
def vfs_ls(path: str = "/") -> str:
    """列出虚拟路径内容，例如 /devices/PLC_1/blocks"""
    if vfs is None:
        raise RuntimeError("VFS 尚未初始化")
    result = vfs.ls(path)
    return "\n".join(result) if isinstance(result, list) else str(result)


@mcp.tool()
def vfs_cat(path: str) -> str:
    """读取文件/程序块内容，例如 /devices/PLC_1/blocks/Main.scl"""
    if vfs is None:
        raise RuntimeError("VFS 尚未初始化")
    return vfs.cat(path)


@mcp.tool()
def vfs_write(path: str, content: str) -> str:
    """写入文件/程序块内容"""
    if vfs is None:
        raise RuntimeError("VFS 尚未初始化")
    vfs.echo(content, path)
    return f"已写入: {path}"


@mcp.tool()
def vfs_diff(path_a: str, path_b: str) -> str:
    """比较两个文件/程序块差异"""
    if vfs is None:
        raise RuntimeError("VFS 尚未初始化")
    return vfs.diff(path_a, path_b)


@mcp.tool()
def vfs_grep(pattern: str, path: str) -> str:
    """在文件/程序块中搜索字符串"""
    if vfs is None:
        raise RuntimeError("VFS 尚未初始化")
    matches = vfs.grep(pattern, path)
    return "\n".join(matches) if isinstance(matches, list) else str(matches)


@mcp.tool()
def vfs_compile() -> str:
    """编译当前 PLC 项目"""
    if vfs is None:
        raise RuntimeError("VFS 尚未初始化")
    result = vfs.adapter.compile()
    return json.dumps(result, ensure_ascii=False, indent=2)


def main() -> None:
    """启动 MCP Server"""
    global vfs

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    adapter = _create_adapter()
    adapter.connect()

    vfs = PLCVirtualFS(adapter)
    logging.info("PLC MCP Server 已启动，品牌: %s", adapter.brand)

    mcp.run()


if __name__ == "__main__":
    main()
