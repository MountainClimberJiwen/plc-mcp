# PLC-Universal-MCP：让 AI 像操作文件一样操控你的 PLC

> 工业自动化 × 大语言模型的跨界实验。一个 MCP 服务器，让 ChatGPT/Claude 直接读写西门子、倍福、罗克韦尔的 PLC 代码。

---

## 一、痛点：为什么 PLC 编程还是这么难？

做工业自动化的工程师都懂：

- **TIA Portal 只有 Windows 版**，Mac 用户只能开虚拟机
- **SCL/STL 代码锁在二进制项目里**，版本管理靠"复制-粘贴-重命名"
- **AI 再强也摸不到 PLC**，因为 IDE 没有开放 API
- **跨品牌迁移痛苦**，西门子转倍福要手动重写一遍

我们习惯了用 `git diff` 看代码变更、用 `grep` 搜变量、用 `cat` 读文件——但 PLC 世界里，这些基本操作都不存在。

---

## 二、解决方案：把 PLC 变成虚拟文件系统

**PLC-Universal-MCP** 的核心思路：**让 AI 用文件语义操作 PLC**。

```python
from plc_vfs import PLCVirtualFS

# 连接 TIA Portal 项目
vfs = PLCVirtualFS(SiemensTIAAdapter("project.ap19"))

# 像操作文件一样读写 PLC
vfs.cat("/devices/PLC_1/blocks/Main.scl")      # 读取主程序
vfs.echo("IF #Start THEN #Motor := TRUE; END_IF;", "/devices/PLC_1/blocks/Main.scl")
vfs.diff("/devices/PLC_1/blocks/Main.scl", "/backup/Main.scl")
vfs.grep("Motor", "/devices/PLC_1/blocks/")    # 搜索所有含 Motor 的块
vfs.cp("/devices/PLC_1/blocks/Main.scl", "/workspace/backup.scl")
```

不需要 TIA Portal 界面，不需要 Windows，不需要鼠标点点点。**一行 Python，AI 直接读写 PLC**。

---

## 三、架构：Mirage VFS  meets  PLC

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
│  │   (虚拟文件系统抽象层)         │            │
│  └──────┬────────────┬──────────┘            │
│         │            │                        │
│  ┌──────▼──┐  ┌──────▼──┐  ┌──────────┐      │
│  │Siemens  │  │Beckhoff │  │Rockwell  │      │
│  │TIA      │  │TwinCAT  │  │Studio    │      │
│  │Adapter  │  │Adapter  │  │5000      │      │
│  └────┬────┘  └────┬────┘  └────┬─────┘      │
│       │            │            │            │
│  ┌────▼────┐  ┌────▼────┐  ┌───▼──────┐     │
│  │TIA      │  │.st 文件 │  │.L5X     │     │
│  │Openness │  │直接读写 │  │导入导出 │     │
│  │(Windows)│  │(全平台) │  │(Windows)│     │
│  └─────────┘  └─────────┘  └─────────┘     │
└─────────────────────────────────────────────┘
```

**关键设计**：
- **文本化优先**：利用各品牌已有的文本导入/导出能力（SCL、.st、L5X），不碰二进制格式
- **跨平台**：Mac/Linux 开发者通过 VFS 远程操作 Windows 上的 TIA Portal
- **品牌无关**：同一套 `cat/echo/diff/grep` 命令，西门子、倍福、罗克韦尔通用

---

## 四、真实场景：AI 自动重构 PLC 代码

### 场景 1：批量变量重命名

```python
# 把所有 "Motor_1" 改成 "Conveyor_Motor"
for block in vfs.ls("/devices/PLC_1/blocks/"):
    content = vfs.cat(block)
    if "Motor_1" in content:
        new_content = content.replace("Motor_1", "Conveyor_Motor")
        vfs.echo(new_content, block)
```

### 场景 2：代码审查

```python
# 导出两个版本的差异
vfs.diff("/devices/PLC_1/blocks/FB_Motor.scl", 
         "/snapshot/2024-01-15/FB_Motor.scl")
# 输出：
# --- FB_Motor.scl (v1.2)
# +++ FB_Motor.scl (v1.3)
# @@ -15,7 +15,7 @@
#  IF #Start THEN
# -    #Speed := 100;
# +    #Speed := 150;  // 提速需求：客户要求 1500 RPM
#      #Run := TRUE;
#  END_IF;
```

### 场景 3：AI 自动生成代码

```python
# 让 Claude 读取现有代码，生成新功能块
context = vfs.cat("/devices/PLC_1/blocks/FB_PID.scl")
prompt = f"基于这个 PID 块，写一个带死区控制的变体。代码：\n{context}"
# Claude 生成新代码...
vfs.echo(generated_code, "/devices/PLC_1/blocks/FB_PID_Deadband.scl")
```

---

## 五、技术亮点

| 特性 | 说明 |
|------|------|
| **纯 Python** | 无 FUSE、无内核模块，pip 安装即用 |
| **MCP 协议** | 原生支持 Claude Desktop、ChatGPT、Cursor |
| **多品牌** | 西门子 TIA、倍福 TwinCAT、罗克韦尔 Studio 5000 |
| **本地/远程** | 直接连接本机 PLC，或通过 SSH 操作远程项目 |
| **Git 友好** | 导出 .scl/.st 文件，天然支持版本控制 |

---

## 六、Quick Start

```bash
# 安装
pip install plc-universal-mcp

# 启动 MCP 服务器
python -m plc_vfs.server --project my_project.ap19 --brand siemens

# 在 Claude Desktop 配置中添加
# {
#   "mcpServers": {
#     "plc": {
#       "command": "python",
#       "args": ["-m", "plc_vfs.server", "--project", "my_project.ap19"]
#     }
#   }
# }
```

然后对 Claude 说：
> "读取我的 Main 程序，把 Motor 启动逻辑改成带互锁的"

---

## 七、为什么是现在？

- **MCP 协议**（Model Context Protocol）刚发布，AI 与工具的标准接口
- **TIA Portal Openness** 已成熟，但只给 C#/.NET，没有 Python 接口
- **TwinCAT** 原生支持 .st 文件，但缺乏统一的 AI 接入层
- **工业 4.0** 喊了十年，PLC 编程方式还是 1990 年代的风格

这个项目不是替代 TIA Portal，而是**给 AI 开一扇门**。

---

## 八、作者 & 支持

**MountainClimberJiwen** — 登山小鲁

工业自动化 × AI 的跨界探索者。相信 PLC 编程应该像写 Python 一样简单。

- 📧 ljwscu@gmail.com
- 💬 微信扫码添加好友（备注 "plc-mcp"）
- ☕ 如果这个项目帮到了你，请我喝杯咖啡

<img src="assets/wechat-contact-qr.jpg" width="200" alt="WeChat QR Code">
<img src="assets/payment-qr.jpg" width="200" alt="Support QR Code">

---

**GitHub**: https://github.com/MountainClimberJiwen/plc-mcp

**License**: MIT

**Stars**: ⭐ 如果对你有用，点个 Star 让更多人看到！
