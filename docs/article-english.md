# PLC-Universal-MCP: Let AI Manipulate Your PLC Like Files

> Industrial Automation × Large Language Models. One MCP server lets ChatGPT/Claude directly read and write Siemens, Beckhoff, and Rockwell PLC code.

---

## The Pain: Why Is PLC Programming Still So Hard?

Every industrial automation engineer knows:

- **TIA Portal is Windows-only**. Mac users are stuck with VMs.
- **SCL/STL code is locked in binary projects**. Version control means "copy-paste-rename."
- **AI is powerful but can't touch PLCs** because IDEs lack open APIs.
- **Cross-brand migration is painful**. Moving from Siemens to Beckhoff means rewriting everything by hand.

We're used to `git diff` for code changes, `grep` for searching variables, `cat` for reading files—but in the PLC world, these basic operations don't exist.

---

## The Solution: Turn Your PLC into a Virtual Filesystem

**PLC-Universal-MCP**'s core idea: **Let AI operate PLCs using file semantics**.

```python
from plc_vfs import PLCVirtualFS

# Connect to a TIA Portal project
vfs = PLCVirtualFS(SiemensTIAAdapter("project.ap19"))

# Read and write PLC code like files
vfs.cat("/devices/PLC_1/blocks/Main.scl")      # Read main program
vfs.echo("IF #Start THEN #Motor := TRUE; END_IF;", "/devices/PLC_1/blocks/Main.scl")
vfs.diff("/devices/PLC_1/blocks/Main.scl", "/backup/Main.scl")
vfs.grep("Motor", "/devices/PLC_1/blocks/")    # Search all blocks containing Motor
vfs.cp("/devices/PLC_1/blocks/Main.scl", "/workspace/backup.scl")
```

No TIA Portal UI. No Windows. No mouse clicking. **One line of Python, AI directly reads and writes your PLC**.

---

## Architecture: Mirage VFS Meets PLC

```
┌─────────────────────────────────────────────┐
│          AI Agent (Claude / ChatGPT)          │
│              "cat /plc/blocks/OB1.scl"        │
└─────────────────┬───────────────────────────┘
                  │ MCP Protocol
┌─────────────────▼───────────────────────────┐
│        PLC-Universal-MCP Server               │
│  ┌─────────────┐  ┌─────────────┐            │
│  │  cat/echo   │  │  diff/grep  │            │
│  │   cp/ls     │  │   mount     │            │
│  └──────┬──────┘  └──────┬──────┘            │
│         │                │                    │
│  ┌──────▼────────────────▼──────┐            │
│  │      PLCVirtualFS Core        │            │
│  │   (Virtual Filesystem Layer)  │            │
│  └──────┬────────────┬──────────┘            │
│         │            │                        │
│  ┌──────▼──┐  ┌──────▼──┐  ┌──────────┐      │
│  │Siemens  │  │Beckhoff │  │Rockwell  │      │
│  │TIA      │  │TwinCAT  │  │Studio    │      │
│  │Adapter  │  │Adapter  │  │5000      │      │
│  └────┬────┘  └────┬────┘  └────┬─────┘      │
│       │            │            │            │
│  ┌────▼────┐  ┌────▼────┐  ┌───▼──────┐     │
│  │TIA      │  │.st Files │  │.L5X     │     │
│  │Openness │  │Direct    │  │Import/  │     │
│  │(Windows)│  │Read/Write│  │Export   │     │
│  └─────────┘  └─────────┘  └─────────┘     │
└─────────────────────────────────────────────┘
```

**Key Design Decisions**:
- **Text-first**: Leverage each brand's existing text import/export capabilities (SCL, .st, L5X). No binary formats.
- **Cross-platform**: Mac/Linux developers operate remote Windows TIA Portal via VFS.
- **Brand-agnostic**: Same `cat/echo/diff/grep` commands work for Siemens, Beckhoff, and Rockwell.

---

## Real-World Scenario: AI Auto-Refactoring PLC Code

### Scenario 1: Batch Variable Renaming

```python
# Rename all "Motor_1" to "Conveyor_Motor"
for block in vfs.ls("/devices/PLC_1/blocks/"):
    content = vfs.cat(block)
    if "Motor_1" in content:
        new_content = content.replace("Motor_1", "Conveyor_Motor")
        vfs.echo(new_content, block)
```

### Scenario 2: Code Review

```python
# Export diff between two versions
vfs.diff("/devices/PLC_1/blocks/FB_Motor.scl", 
         "/snapshot/2024-01-15/FB_Motor.scl")
# Output:
# --- FB_Motor.scl (v1.2)
# +++ FB_Motor.scl (v1.3)
# @@ -15,7 +15,7 @@
#  IF #Start THEN
# -    #Speed := 100;
# +    #Speed := 150;  // Speed increase: customer requires 1500 RPM
#      #Run := TRUE;
#  END_IF;
```

### Scenario 3: AI-Generated Code

```python
# Let Claude read existing code and generate a new function block
context = vfs.cat("/devices/PLC_1/blocks/FB_PID.scl")
prompt = f"Based on this PID block, write a deadband variant. Code:\n{context}"
# Claude generates new code...
vfs.echo(generated_code, "/devices/PLC_1/blocks/FB_PID_Deadband.scl")
```

---

## Technical Highlights

| Feature | Description |
|---------|-------------|
| **Pure Python** | No FUSE, no kernel modules. `pip install` and go. |
| **MCP Protocol** | Native support for Claude Desktop, ChatGPT, Cursor |
| **Multi-brand** | Siemens TIA, Beckhoff TwinCAT, Rockwell Studio 5000 |
| **Local/Remote** | Direct local PLC connection or SSH to remote projects |
| **Git-friendly** | Export .scl/.st files, naturally version-controllable |

---

## Quick Start

```bash
# Install
pip install plc-universal-mcp

# Start MCP server
python -m plc_vfs.server --project my_project.ap19 --brand siemens

# Add to Claude Desktop config
# {
#   "mcpServers": {
#     "plc": {
#       "command": "python",
#       "args": ["-m", "plc_vfs.server", "--project", "my_project.ap19"]
#     }
#   }
# }
```

Then tell Claude:
> "Read my Main program and change the Motor start logic to include interlocking"

---

## Why Now?

- **MCP Protocol** (Model Context Protocol) just launched—the standard interface for AI tools.
- **TIA Portal Openness** is mature but only offers C#/.NET, no Python bindings.
- **TwinCAT** natively supports .st files but lacks a unified AI access layer.
- **Industry 4.0** has been a buzzword for a decade, yet PLC programming remains stuck in the 1990s.

This project doesn't replace TIA Portal. It **opens a door for AI**.

---

## Author & Support

**MountainClimberJiwen** — 登山小鲁

An explorer at the intersection of industrial automation and AI. Believes PLC programming should be as simple as writing Python.

- 📧 ljwscu@gmail.com
- 💬 WeChat QR code below (mention "plc-mcp")
- ☕ If this project helped you, buy me a coffee

<img src="assets/wechat-contact-qr.jpg" width="200" alt="WeChat QR Code">
<img src="assets/payment-qr.jpg" width="200" alt="Support QR Code">

---

**GitHub**: https://github.com/MountainClimberJiwen/plc-mcp

**License**: MIT

**Stars**: ⭐ If this helps you, give it a Star so more people can find it!
