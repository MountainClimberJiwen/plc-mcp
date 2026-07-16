import os
import sys
import logging
from contextlib import closing
from pathlib import Path
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from pydantic import AnyUrl
from typing import Any
from .demo_1 import TiaProject


logger = logging.getLogger('plc-mcp-server')
logger.info("Starting PLC MCP Server")


def _add_tia_dll_reference():
    """Load Siemens.Engineering.dll from TIA_OPENNESS_DLL_PATH or common install paths."""
    import clr
    dll_path = os.environ.get('TIA_OPENNESS_DLL_PATH')
    if dll_path and os.path.exists(dll_path):
        clr.AddReference(dll_path)
        return
    # Fallback to common TIA Portal V19 paths
    for candidate in (
        r'E:\Program Files\Siemens\Automation\Portal V19\Bin\PublicAPI\Siemens.Engineering.dll',
        r'C:\Program Files\Siemens\Automation\Portal V19\Bin\PublicAPI\Siemens.Engineering.dll',
    ):
        if os.path.exists(candidate):
            clr.AddReference(candidate)
            return
    logging.warning('Siemens.Engineering.dll not found; TIA Openness calls may fail')


def _create_vfs_adapter(brand: str, project_path: str, host: str = None, port: int = 502):
    """
    根据品牌创建对应的 VFS 适配器

    Args:
        brand: 'siemens' | 'inovance' | 'mock'
        project_path: TIA 项目路径或 Inovance 块映射文件路径
        host: Inovance PLC 的 IP 地址（仅 inovance 使用）
        port: Modbus TCP 端口（默认 502）
    """
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    )

    from plc_vfs import PLCVirtualFS
    from plc_vfs.adapters.inovance import InovanceAM600Adapter, MockInovanceAdapter

    if brand == "siemens":
        _add_tia_dll_reference()
        # SiemensTIAAdapter 在 core.py 中定义
        from plc_vfs.core import SiemensTIAAdapter
        adapter = SiemensTIAAdapter(project_path)
        logger.info("VFS: Siemens TIA Adapter initialized")

    elif brand == "inovance":
        # 优先使用真实 PLC 连接，如果连接失败则使用 Mock
        block_map = project_path if os.path.exists(project_path) else None
        if not block_map:
            # 尝试默认配置路径
            default_map = os.path.join(
                os.path.dirname(__file__), '..', '..', '..',
                'config', 'inovance_blocks.json'
            )
            if os.path.exists(default_map):
                block_map = default_map

        host = host or os.environ.get('INOVANCE_PLC_HOST', '192.168.1.10')
        try:
            adapter = InovanceAM600Adapter(
                host=host,
                port=port,
                block_map_path=block_map,
            )
            adapter.connect()
            logger.info(f"VFS: Inovance AM600 Adapter connected to {host}:{port}")
        except Exception as e:
            logger.warning(f"Failed to connect to Inovance PLC: {e}")
            logger.info("Falling back to MockInovanceAdapter")
            adapter = MockInovanceAdapter(block_map_path=block_map)
            adapter.connect()

    elif brand == "mock":
        # 通用 Mock 适配器（用于测试）
        block_map = project_path if os.path.exists(project_path) else None
        if not block_map:
            default_map = os.path.join(
                os.path.dirname(__file__), '..', '..', '..',
                'config', 'inovance_blocks.json'
            )
            if os.path.exists(default_map):
                block_map = default_map
        adapter = MockInovanceAdapter(block_map_path=block_map)
        adapter.connect()
        logger.info("VFS: Mock Inovance Adapter initialized")

    else:
        raise ValueError(f"Unknown brand: {brand}. Supported: siemens, inovance, mock")

    return PLCVirtualFS(adapter)


# reconfigure UnicodeEncodeError prone default (i.e. windows-1252) to utf-8
if sys.platform == "win32" and os.environ.get('PYTHONIOENCODING') is None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


async def main(
    project_path: str,
    project_name: str,
    use_vfs: bool = False,
    brand: str = "siemens",
    host: str = None,
    port: int = 502,
):
    logger.info(
        f"Starting PLC MCP Server: brand={brand}, "
        f"project_path={project_path}, project_name={project_name}"
    )

    server = Server("plc-mcp-server")
    tia_project = TiaProject(project_path, project_name)
    PROJECT_PATH = project_path
    PROJECT_NAME = project_name

    # Optional Virtual Filesystem integration layer
    vfs = None
    if use_vfs:
        try:
            vfs = _create_vfs_adapter(brand, project_path, host=host, port=port)
            logger.info(f"VFS integration enabled ({brand})")
        except Exception as e:
            logger.error(f"Failed to initialize VFS: {e}")
            vfs = None
    else:
        logger.info("VFS integration disabled")

    print("init tia project")
    # tia_project.open_project()
    # Register handlers
    logger.debug("Registering handlers")

    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        logger.debug("Handling list_resources request")
        return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> str:
        pass

    @server.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        logger.debug("Handling list_prompts request")
        return []

    @server.get_prompt()
    async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        logger.debug(f"Handling get_prompt request for {name} with args {arguments}")
        prompt = ""
        return types.GetPromptResult(
            description=f"",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=prompt.strip()),
                )
            ],
        )

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available tools"""
        tools = [
        # open project
        types.Tool(
            name="open-project",
            description="Open a PLC project",
            inputSchema={
                "type": "object",
            },
        ),
        # 增加一个tool，来连接plc 设备，输入参数是plc的名字
        types.Tool(
            name="connect-plc",
            description="Connect to a PLC device",
            inputSchema={
                "type": "object",
                "properties": {
                    "plc_name": {"type": "string"},
                },
                "required": ["plc_name"],
            },
        ),
        # 增加一个tool，来初始化PLC设备，输入参数是项目和PLC的名字
        types.Tool(
            name="init-plc",
            description="Initialize a PLC device",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "plc_name": {"type": "string"},
                },
                "required": ["project", "plc_name"],
            },
        ),
        # 增加一个tool，来更新PLC块，输入参数是和XML路径
        types.Tool(
            name="update-plc-block",
            description="Update a PLC block with an absolute XML path",
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_xml_path": {"type": "string", "description": "The absolute path of the XML file"},
                },
                "required": ["absolute_xml_path"],
            },
        )
        ]

        if vfs:
            tools.extend([
                types.Tool(
                    name="vfs-ls",
                    description="List PLC blocks or directories via the virtual filesystem",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "/devices/PLC_1/blocks"},
                        },
                    },
                ),
                types.Tool(
                    name="vfs-cat",
                    description="Read a PLC block source via the virtual filesystem",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                        },
                        "required": ["path"],
                    },
                ),
                types.Tool(
                    name="vfs-write",
                    description="Write source code to a PLC block via the virtual filesystem",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                ),
                types.Tool(
                    name="vfs-diff",
                    description="Diff two PLC blocks via the virtual filesystem",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path_a": {"type": "string"},
                            "path_b": {"type": "string"},
                        },
                        "required": ["path_a", "path_b"],
                    },
                ),
            ])

        return tools

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution requests"""
        arguments = arguments or {}
        try:
            if name == "open-project":
                project_path = PROJECT_PATH
                project_name = PROJECT_NAME
                if not project_path or not project_name:
                    raise ValueError("Missing project_path or project_name")

                if vfs:
                    vfs.adapter.connect()
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Connected to project '{project_name}' via VFS ({brand})",
                        )
                    ]

                tia_project = TiaProject(project_path, project_name)
                tia_project.open_project()
                return [
                    types.TextContent(
                        type="text",
                        text=f"Opened project '{project_name}' at '{project_path}'",
                    )
                ]

            elif name == "update-plc-block":
                xml_path = arguments.get("absolute_xml_path")
                if not xml_path:
                    raise ValueError("Missing xml_path")
                tia_project = TiaProject(PROJECT_PATH, PROJECT_NAME)
                tia_project.update_plc_block(xml_path)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Updated PLC block with XML path '{xml_path}'",
                    )
                ]
            elif name == "vfs-ls" and vfs:
                path = arguments.get("path", "/devices/PLC_1/blocks")
                items = vfs.ls(path)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Items under {path}:\n" + "\n".join(items),
                    )
                ]
            elif name == "vfs-cat" and vfs:
                path = arguments.get("path")
                if not path:
                    raise ValueError("Missing path")
                content = vfs.cat(path)
                return [
                    types.TextContent(
                        type="text",
                        text=f"--- {path} ---\n{content}",
                    )
                ]
            elif name == "vfs-write" and vfs:
                path = arguments.get("path")
                content = arguments.get("content")
                if not path or content is None:
                    raise ValueError("Missing path or content")
                vfs.echo(content, path)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Wrote to {path} via VFS",
                    )
                ]
            elif name == "vfs-diff" and vfs:
                path_a = arguments.get("path_a")
                path_b = arguments.get("path_b")
                if not path_a or not path_b:
                    raise ValueError("Missing path_a or path_b")
                diff = vfs.diff(path_a, path_b)
                return [
                    types.TextContent(
                        type="text",
                        text=diff or "No differences",
                    )
                ]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="plc-mcp-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
