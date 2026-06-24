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

# from demo_1 import TiaProject
# from demo import init_project, init_plc, update_plc_block
# reconfigure UnicodeEncodeError prone default (i.e. windows-1252) to utf-8
if sys.platform == "win32" and os.environ.get('PYTHONIOENCODING') is None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

logger = logging.getLogger('plc-mcp-server')
logger.info("Starting PLC MCP Server")

# PROMPT_TEMPLATE = """
# The assistants goal is to help the user to develop a plc project.
# Here is some more information about mcp and this specific mcp server:
# <mcp>
# Prompts:

# </mcp>
# """

async def main(project_path: str, project_name: str):
    logger.info(f"Starting PLC MCP Server with project path: {project_path} and project name: {project_name}")

    server = Server("plc-mcp-server")
    tia_project = TiaProject(project_path, project_name)
    PROJECT_PATH = project_path
    PROJECT_NAME = project_name
    print("init tia project")
    # tia_project.open_project()
    # Register handlers
    logger.debug("Registering handlers")

    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        logger.debug("Handling list_resources request")
        return [
            # types.Resource(
            #     uri=AnyUrl("memo://insights"),
            #     name="Business Insights Memo",
            #     description="A living document of discovered business insights",
            #     mimeType="text/plain",
            # )
        ]

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> str:
        # logger.debug(f"Handling read_resource request for URI: {uri}")
        # if uri.scheme != "memo":
        #     logger.error(f"Unsupported URI scheme: {uri.scheme}")
        #     raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

        # path = str(uri).replace("memo://", "")
        # if not path or path != "insights":
        #     logger.error(f"Unknown resource path: {path}")
        #     raise ValueError(f"Unknown resource path: {path}")

        # return db._synthesize_memo()
        pass

    @server.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        logger.debug("Handling list_prompts request")
        return [
            # types.Prompt(
            #     name="mcp-demo",
            #     description="A prompt to seed the database with initial data and demonstrate what you can do with an SQLite MCP Server + Claude",
            #     arguments=[
            #         types.PromptArgument(
            #             name="topic",
            #             description="Topic to seed the database with initial data",
            #             required=True,
            #         )
            #     ],
            # )
        ]

    @server.get_prompt()
    async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        logger.debug(f"Handling get_prompt request for {name} with args {arguments}")
        # if name != "mcp-demo":
        #     logger.error(f"Unknown prompt: {name}")
        #     raise ValueError(f"Unknown prompt: {name}")

        # if not arguments or "topic" not in arguments:
        #     logger.error("Missing required argument: topic")
        #     raise ValueError("Missing required argument: topic")

        # topic = arguments["topic"]
        # prompt = PROMPT_TEMPLATE.format(topic=topic)
        prompt = ""
        # logger.debug(f"Generated prompt template for topic: {topic}")
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
        return [
        # open project
        types.Tool(
            name="open-project",
            description="Open a PLC project",
            inputSchema={
                "type": "object",
                # "properties": {
                #     "project_path": {"type": "string"},
                #     "project_name": {"type": "string"},
                # },
                # "required": ["project_path", "project_name"],
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

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution requests"""
        try:
            if name == "open-project":
                project_path = PROJECT_PATH
                project_name = PROJECT_NAME
                if not project_path or not project_name:
                    raise ValueError("Missing project_path or project_name")
                
                tia_project = TiaProject(project_path, project_name)
                tia_project.open_project()
                return [
                    types.TextContent(
                        type="text",
                        text=f"Opened project '{project_name}' at '{project_path}'",
                    )
                ]
            # elif name == "init-project":
            #     project_path = arguments.get("project_path")
            #     project_name = arguments.get("project_name")
            #     if not project_path or not project_name:
            #         raise ValueError("Missing project_path or project_name")
            #     # Call the init_project function from demo.py
            #     myproject = init_project(project_path, project_name)
            #     return [
            #         types.TextContent(
            #             type="text",
            #             text=f"Initialized project '{project_name}' at '{project_path}'",
            #         )
            #     ]
            # elif name == "init-plc":
            #     project = arguments.get("project")
            #     plc_name = arguments.get("plc_name")
            #     if not project or not plc_name:
            #         raise ValueError("Missing project or plc_name")
            #     # Call the init_plc function from demo.py

            #     plc_device = init_plc(project, plc_name)
            #     return [
            #         types.TextContent(
            #             type="text",
            #             text=f"Initialized PLC '{plc_name}' in project",
            #         )
            #     ]
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
