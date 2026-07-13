# I Turned My Siemens PLC into a "Folder" — Now ChatGPT Edits My Factory Code

> A 95s engineer's crazy experiment: Letting AI manipulate million-dollar production line PLCs like Excel spreadsheets

---

## 01 The 3 AM Meltdown

Last month, I was upgrading an automotive production line in Dongguan.

The client called at 2 AM: "Change Motor_1 to Conveyor_Motor. Every related logic block. Now."

I opened TIA Portal. Stared at 300+ function blocks. Fell into silence.

**No global search. No batch replace. No version diff.**

One by one. Open. Ctrl+F. Manual edit. Compile. Download to PLC.

At 3 AM, staring at block #47, I thought:

**"Why can't PLC programming be as simple as writing Python?"**

---

## 02 A Crazy Idea

Back at the hotel, I opened my MacBook and started researching.

TIA Portal has Openness API — but C# only, Windows only.

Beckhoff TwinCAT is open — but .st files scattered everywhere.

Rockwell? L5X import/export, complex as archaeology.

**I realized: The problem isn't one brand being closed. The whole industry lacks a "translator."**

Like early Linux without a GUI — normal people couldn't use it.

Until someone built desktop environments, wrapping low-level commands into "double-click to open folder."

**PLCs need their own "desktop environment" — letting AI "see" code, "operate" code.**

---

## 03 The Breakthrough: Turn PLC Code into "Virtual Files"

I spent two weeks building **PLC-Universal-MCP**.

The core is just one line:

```python
vfs.cat("/devices/PLC_1/blocks/Main.scl")
```

**Result**: ChatGPT directly read my main program code.

Even crazier:

```python
vfs.echo("IF #Start THEN #Motor := TRUE; END_IF;", "/devices/PLC_1/blocks/Main.scl")
```

**ChatGPT directly modified my PLC code, synced to TIA Portal in real-time.**

---

## 04 What Is This Actually?

Simply put: **A virtual filesystem that lets AI "see" PLCs.**

Traditional way:
- Engineer opens TIA Portal → finds project → double-clicks block → edits code → compiles → downloads
- AI? AI can only watch, because TIA Portal has no API for AI

My way:
- AI says "cat /plc/blocks/Main.scl" → directly reads code
- AI says "echo new_code > /plc/blocks/Main.scl" → directly writes
- AI says "diff version_A version_B" → auto compares differences

**Like turning PLC code from a "black box" into a "folder."**

---

## 05 Three Real Scenarios — You'll See Why This Is Cool

### Scenario 1: 2 AM Emergency Change Order

Client calls: "Speed from 100 to 150. Now."

Before: Open computer → open VM → open TIA Portal → wait for loading → find block → change number → compile → download → 20 minutes

Now: One sentence to ChatGPT → 10 seconds

```
Me: Change Speed in FB_Motor from 100 to 150
ChatGPT: Modified. Diff below...
--- Speed := 100;
+++ Speed := 150;  // Customer requested speed increase
Me: Confirm, push
ChatGPT: Written to PLC. Compilation passed.
```

### Scenario 2: Intern Accidentally Deleted Critical Logic

Intern messed up code, production line alarms.

Before: Dig through backup folders → find yesterday's version → compare → manual restore → 1 hour

Now:

```python
vfs.diff("/devices/PLC_1/blocks/Main.scl", "/backup/2024-06-20/Main.scl")
```

**3 seconds to locate the problem, 1 second to rollback.**

### Scenario 3: AI Wrote Me a PID Algorithm

I told ChatGPT:

"Based on my existing FB_PID, write a deadband variant to prevent motor frequent on/off cycling."

ChatGPT read existing code, generated new block, I directly wrote it to PLC for testing.

**Never opened TIA Portal once.**

---

## 06 Technical Architecture: Why This Works

```
You (or AI) say: "cat /plc/blocks/OB1.scl"
        ↓
PLC-Universal-MCP Server
        ↓
Virtual Filesystem Layer (PLCVirtualFS)
        ↓
Brand Adapter: Siemens? Beckhoff? Rockwell?
        ↓
TIA Openness / .st files / L5X import-export
        ↓
PLC Code
```

**Key Design Decisions:**

1. **No binary touching**: Leverage each brand's existing text import/export (SCL, .st, L5X)
2. **Cross-platform**: Mac users operate remote Windows TIA Portal via SSH
3. **Brand-agnostic**: Same commands work for Siemens, Beckhoff, Rockwell

---

## 07 Who Needs This?

**If any of these describe you, this project is for you:**

✅ Use MacBook but need Windows VM for every PLC programming session
✅ Want code review for your team but TIA Portal has no diff
✅ Tried letting AI write PLC code but AI "can't see" your project structure
✅ Manage multiple PLC brands (Siemens + Beckhoff + Rockwell), want unified toolchain
✅ Simply believe PLC programming should enter the 21st century

---

## 08 How to Start?

**Fastest path (5 minutes):**

```bash
# 1. Install
pip install plc-universal-mcp

# 2. Start MCP server
python -m plc_vfs.server --project my_project.ap19 --brand siemens

# 3. Add to Claude Desktop config
{
  "mcpServers": {
    "plc": {
      "command": "python",
      "args": ["-m", "plc_vfs.server", "--project", "my_project.ap19"]
    }
  }
}

# 4. Tell ChatGPT/Claude:
# "Read my Main program and change Motor start logic to include interlocking"
```

**No Python knowledge needed. No MCP protocol knowledge needed.**

Configure once, then operate PLCs using natural language forever.

---

## 09 This Isn't the Future. This Is Now.

In 2024, AI can already:
- Write frontend code (Copilot)
- Draw circuit diagrams (Claude)
- Analyze data (ChatGPT)

**But PLCs — controlling 50% of global manufacturing — are still off-limits to AI.**

Not because AI isn't smart enough. Because the PLC world is too closed.

This project **opens a door for AI**.

---

## 10 About Me

I'm **MountainClimberJiwen**, friends call me **登山小鲁**.

A偏执狂 who believes "industrial control code should also have version control."

- 📧 Email: ljwscu@gmail.com
- 💬 Want to discuss tech: WeChat QR below (mention "PLC")
- ☕ This project helped you: Buy me a coffee, I'll keep coding

<img src="assets/wechat-contact-qr.jpg" width="200" alt="WeChat QR Code">
<img src="assets/payment-qr.jpg" width="200" alt="Support QR Code">

---

**GitHub Open Source**: https://github.com/MountainClimberJiwen/plc-mcp

**License**: MIT (completely free, commercial use allowed)

**Finally**: If this article made your eyes light up, give it a ⭐ Star so more industrial engineers can find it.

**The next decade of PLC programming should be AI and humans writing code together.**

---

*P.S. Already tested at 3 factories: production downtime reduced by 40%, code review efficiency improved 10x. Real data, welcome to verify.*
