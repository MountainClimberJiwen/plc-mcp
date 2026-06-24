import asyncio

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio

# Store notes as a simple key-value dict to demonstrate state management
notes: dict[str, str] = {"hello": "world"}

# Store greetings as a simple dict
greetings: dict[str, str] = {"world": "Hello, world!"}

# Initialize the project in the server constructor
server = Server("plc-tool")

# Initialize the TIA project when the server starts
# project_path = "E:\\TIA_Projects\\test3"  # Example path, adjust as needed
# project_name = 'SimpleCounter2'  # Example name, adjust as needed
# from simple_tool.demo import init_project, init_plc, update_plc_block
# myproject = init_project(project_path, project_name)


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    List available note and greeting resources.
    Each note is exposed as a resource with a custom note:// URI scheme.
    Each greeting is exposed as a resource with a custom greeting:// URI scheme.
    """
    resources = [
        types.Resource(
            uri=AnyUrl(f"note://internal/{name}"),
            name=f"Note: {name}",
            description=f"A simple note named {name}",
            mimeType="text/plain",
        )
        for name in notes

        # [
        # types.Resource(
        #     uri=AnyUrl(f"note://internal/{name}"),
        #     name=f"Greeting: {name}",
        #     description=f"A greeting for {name}",
        #     mimeType="text/plain",
        # )
        # for name in greetings
    # ]
    ]
    
    resources.extend([
        types.Resource(
            uri=AnyUrl(f"greeting://internal/{name}"),
            name=f"Greeting: {name}",
            description=f"A greeting for {name}",
            mimeType="text/plain",
        )
        for name in greetings
    ])
    
    return resources

@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """
    Read a specific note or greeting content by its URI.
    The name is extracted from the URI path component.
    """
    if uri.scheme == "note":
        name = uri.path
        if name is not None:
            name = name.lstrip("/")
            return notes[name]
        raise ValueError(f"Note not found: {name}")
    elif uri.scheme == "greeting":
        name = uri.path
        if name is not None:
            name = name.lstrip("/")
            return greetings.get(name, f"Hello, {name}!")
        raise ValueError(f"Invalid greeting name: {name}")
    else:
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """
    List available prompts.
    Each prompt can have optional arguments to customize its behavior.
    """
    return [
        types.Prompt(
            name="summarize-notes",
            description="Creates a summary of all notes",
            arguments=[
                types.PromptArgument(
                    name="style",
                    description="Style of the summary (brief/detailed)",
                    required=False,
                )
            ],
        )
    ]

@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """
    Generate a prompt by combining arguments with server state.
    The prompt includes all current notes and can be customized via arguments.
    """
    if name != "summarize-notes":
        raise ValueError(f"Unknown prompt: {name}")

    style = (arguments or {}).get("style", "brief")
    detail_prompt = " Give extensive details." if style == "detailed" else ""

    return types.GetPromptResult(
        description="Summarize the current notes",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"Here are the current notes to summarize:{detail_prompt}\n\n"
                    + "\n".join(
                        f"- {name}: {content}"
                        for name, content in notes.items()
                    ),
                ),
            ),
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"Here is the current project: {myproject}",
                ),
            ),
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"Here is the current PLC: {plc_device}",
                ),
            )
            
        ],
    )

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="add-note",
            description="Add a new note",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["name", "content"],
            },
        ),
        types.Tool(
            name="greet",
            description="Returns a hello greeting to someone",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
                "required": ["name"],
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
        # 增加一个tool，来初始化项目，输入参数是项目路径和项目名称
        types.Tool(
            name="init-project",
            description="Initialize a TIA project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "project_name": {"type": "string"},
                },
                "required": ["project_path", "project_name"],
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
        # 增加一个tool，来更新PLC块，输入参数是PLC软件和XML路径
        types.Tool(
            name="update-plc-block",
            description="Update a PLC block with an XML path",
            inputSchema={
                "type": "object",
                "properties": {
                    "plc_sw": {"type": "string"},
                    "xml_path": {"type": "string"},
                },
                "required": ["plc_sw", "xml_path"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """
    if name == "add-note":
        if not arguments:
            raise ValueError("Missing arguments")

        note_name = arguments.get("name")
        content = arguments.get("content")

        if not note_name or not content:
            raise ValueError("Missing name or content")

        # Update server state
        notes[note_name] = content

        # Notify clients that resources have changed
        await server.request_context.session.send_resource_list_changed()

        return [
            types.TextContent(
                type="text",
                text=f"Added note '{note_name}' with content: {content}",
            )
        ]
    elif name == "greet":
        return [
            types.TextContent(
                type="text",
                text=f"Hello, {arguments.get('name', 'world')}!",
            )
        ]
    elif name == "connect-plc":
        plc_name = arguments.get("plc_name")
        if not plc_name:
            raise ValueError("Missing plc_name")
        return [
            types.TextContent(
                type="text",
                text=f"Connected to PLC '{plc_name}'",
            )
        ]
    elif name == "init-project":
        project_path = arguments.get("project_path")
        project_name = arguments.get("project_name")
        if not project_path or not project_name:
            raise ValueError("Missing project_path or project_name")
        # Call the init_project function from demo.py
        myproject = init_project(project_path, project_name)
        return [
            types.TextContent(
                type="text",
                text=f"Initialized project '{project_name}' at '{project_path}'",
            )
        ]
    elif name == "init-plc":
        project = arguments.get("project")
        plc_name = arguments.get("plc_name")
        if not project or not plc_name:
            raise ValueError("Missing project or plc_name")
        # Call the init_plc function from demo.py

        plc_device = init_plc(project, plc_name)
        return [
            types.TextContent(
                type="text",
                text=f"Initialized PLC '{plc_name}' in project",
            )
        ]
    elif name == "update-plc-block":
        plc_sw = arguments.get("plc_sw")
        xml_path = arguments.get("xml_path")
        if not plc_sw or not xml_path:
            raise ValueError("Missing plc_sw or xml_path")
        # Call the update_plc_block function from demo.py
        update_plc_block(plc_sw, xml_path)
        return [
            types.TextContent(
                type="text",
                text=f"Updated PLC block with XML path '{xml_path}'",
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="simple-tool",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )