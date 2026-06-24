"""
PLC Universal MCP
=================
让 AI 用自然语言控制任何品牌的 PLC。

通过虚拟文件系统（VFS）把西门子 TIA Portal、Beckhoff TwinCAT、
Rockwell Studio 5000 等 PLC 项目映射为统一的文件路径，
AI 可以直接用 cat、diff、grep 操作程序块，无需学习各品牌的专有 API。

支持本地映射（开发机直连 IDE）和远程映射（SSH/S3），
让跨平台、跨品牌的 PLC 开发像操作 Git 仓库一样简单。

Quick Start
-----------
```python
from plc_vfs import PLCVirtualFS
from plc_vfs.adapters.siemens import SiemensTIAAdapter

# 1. 连接 TIA Portal（本地）
adapter = SiemensTIAAdapter(project_path="E:/tia/test/test.ap19")
adapter.connect()

# 2. 创建虚拟文件系统
vfs = PLCVirtualFS(adapter)

# 3. 像操作文件一样操作 PLC
print(vfs.cat("/devices/PLC_1/blocks/Block_1.scl"))
vfs.echo("new code", "/devices/PLC_1/blocks/Block_1.scl")
print(vfs.diff("/devices/PLC_1/blocks/Block_1.scl", "/backup/Block_1.scl"))
```

Architecture
------------
```
AI Agent (Claude/Cursor)
    │ MCP Protocol
    ▼
┌─────────────────────────────────────┐
│  PLC Universal MCP Server           │
│  ├── plc_vfs (虚拟文件系统)          │
│  │   ├── adapters/ (品牌适配器)      │
│  │   │   ├── siemens.py (TIA)       │
│  │   │   ├── beckhoff.py (TwinCAT)  │
│  │   │   └── rockwell.py (Logix)    │
│  │   ├── transpiler/ (代码转换)       │
│  │   └── mounts/ (挂载点)            │
│  └── mcp_server/ (MCP 工具)         │
└─────────────────────────────────────┘
    │
    ├──────────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼
┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│TIA     │ │TwinCAT   │ │Studio    │ │EcoStrux. │
│Portal  │ │(Win/Lin) │ │5000      │ │          │
│(Windows)│ │          │ │          │ │          │
└────────┘ └──────────┘ └──────────┘ └──────────┘
```

Supported Brands
----------------
| Brand | Adapter | Status | Text Import | Text Export | Notes |
|-------|---------|--------|-------------|-------------|-------|
| Siemens TIA Portal | `siemens.py` | ✅ Ready | Openness API | Openness API | Windows only |
| Beckhoff TwinCAT | `beckhoff.py` | 🚧 WIP | Native | Native | Most open |
| Rockwell Studio 5000 | `rockwell.py` | 📋 Planned | L5X/L5K | L5X/L5K | Limited SDK |
| Schneider EcoStruxure | `schneider.py` | 📋 Planned | XEF/XML | XEF/XML | REST API |

Key Features
------------
- **本地文件映射**: 把 PLC 项目映射为 `/devices/PLC_1/blocks/*.scl`，
  无需网络，开发机直连 IDE 即可使用
- **跨品牌代码迁移**: SCL ↔ IEC 61131-3 ST ↔ TwinCAT ST 自动转换
- **版本控制**: 导出块到 Git/S3，实现 diff、merge、rollback
- **AI 原生**: MCP Tools 让 Claude/Cursor 直接读写 PLC 代码
- **缓存层**: 减少 IDE API 调用，提升响应速度
- **快照**: 编译前保存项目状态，失败自动回滚

Installation
------------
```bash
# 1. Clone
https://github.com/MountainClimberJiwen/plc-mcp.git
cd plc-mcp

# 2. Install (Python >= 3.10)
pip install -e ".[siemens]"

# 3. Windows: 配置 TIA Openness
powershell scripts/setup_tia_openness.ps1
```

Usage
-----
### 1. 本地映射（推荐）
```python
from plc_vfs import PLCVirtualFS
from plc_vfs.adapters.siemens import SiemensTIAAdapter

# TIA Portal 在本地 Windows 机器
adapter = SiemensTIAAdapter(project_path="E:/tia/test/test.ap19")
adapter.connect()

vfs = PLCVirtualFS(adapter)

# 读取
print(vfs.cat("/devices/PLC_1/blocks/Block_1.scl"))

# 写入
vfs.echo("new scl code", "/devices/PLC_1/blocks/Block_1.scl")

# 比较
print(vfs.diff("/devices/PLC_1/blocks/Block_1.scl", "/backup/Block_1.scl"))

# 搜索
for line in vfs.grep("Motor", "/devices/PLC_1/blocks/*.scl"):
    print(line)
```

### 2. 挂载本地工作区
```python
# 把真实目录挂载到虚拟路径
vfs.mount("/workspace", "C:/Users/dev/plc_workspace")

# 导出块到本地
vfs.cp("/devices/PLC_1/blocks/Block_1.scl", "/workspace/Block_1_backup.scl")

# 从本地导入
vfs.cp("/workspace/new_block.scl", "/devices/PLC_1/blocks/New_Block.scl")
```

### 3. MCP Server 模式
```bash
# 启动 MCP Server（stdio 模式，供 Claude/Cursor 使用）
python -m mcp_server

# 或 HTTP 模式
python -m web_server --port 8080
```

### 4. 跨品牌迁移
```python
from plc_vfs.transpiler import SCLTranspiler

# 从 Siemens 读取
siemens = PLCVirtualFS(SiemensTIAAdapter("E:/tia/test.ap19"))
code = siemens.cat("/devices/PLC_1/blocks/Motor_FB.scl")

# 转换为标准 IEC 61131-3
iec_code = SCLTranspiler.siemens_to_iec(code)

# 转换为 Beckhoff TwinCAT
beckhoff_code = SCLTranspiler.iec_to_beckhoff(iec_code)

# 写入 TwinCAT
beckhoff = PLCVirtualFS(BeckhoffTwinCATAdapter("C:/TC/Project.tcproj"))
beckhoff.echo(beckhoff_code, "/devices/PLC_1/blocks/Motor_FB.st")
```

Project Structure
-----------------
```
plc-universal-mcp/
├── src/
│   ├── plc_vfs/              # 虚拟文件系统核心
│   │   ├── core.py           # VFS 实现 (cat, echo, diff, grep)
│   │   ├── adapters/         # 品牌适配器
│   │   │   ├── base.py       # 适配器基类
│   │   │   ├── siemens.py    # TIA Portal (pythonnet)
│   │   │   ├── beckhoff.py   # TwinCAT (native text)
│   │   │   └── mock.py       # Mock 适配器 (测试)
│   │   ├── transpiler/       # 代码转换器
│   │   │   └── scl_transpiler.py
│   │   └── mounts/           # 挂载点管理
│   │       ├── local.py      # 本地磁盘
│   │       ├── git.py        # Git 仓库
│   │       └── s3.py         # S3 存储
│   ├── mcp_server/           # MCP 服务器
│   │   ├── server.py         # 主入口
│   │   └── tools.py          # MCP Tools 定义
│   └── web_server/           # HTTP API
│       └── app.py
├── tests/                    # 测试套件
├── examples/                 # 示例代码
├── docs/                     # 文档
├── scripts/                  # 安装脚本
└── config/                   # 配置文件模板
```

Why Virtual Filesystem?
-----------------------
PLC 编程的核心矛盾：
- **STL/SCL 是文本语言** — 天然适合版本控制、diff、AI 生成
- **但各品牌 IDE 把代码锁在二进制项目里** — 无法直接读取

PLC-VFS 解决这个矛盾：
1. **不改动 IDE** — 通过 Openness API / SDK 读写
2. **统一接口** — 所有品牌用相同的 `cat/echo/diff/grep`
3. **本地优先** — 无需网络，开发机直连即可工作
4. **AI 原生** — MCP Protocol 让 AI 直接操作

Author & Contact
----------------

**MountainClimberJiwen** — 登山小鲁

工业自动化 × AI 的跨界探索者。相信 PLC 编程应该像写 Python 一样简单。

- 📧 Email: ljwscu@gmail.com
- 💬 WeChat: 扫码添加好友，备注 "plc-mcp"
  
  <img src="assets/wechat-contact-qr.jpg" width="200" alt="WeChat QR Code">

- 🐙 GitHub: [@MountainClimberJiwen](https://github.com/MountainClimberJiwen)

Support This Project
--------------------

如果这个项目帮你节省了调试时间、减少了加班、或者让你对 PLC 编程有了新的认识，欢迎请我喝杯咖啡 ☕

你的支持会转化为：
- 更多品牌适配器（Beckhoff、Rockwell、Schneider...）
- 更好的文档和教程
- 更稳定的代码和更快的 bug 修复

**Buy Me a Coffee** 🍵

<img src="assets/payment-qr.jpg" width="200" alt="Support QR Code">

> "每一杯咖啡，都是对一个工程师深夜写代码的温柔慰藉。"

License
-------
MIT

Contributors
------------
- MountainClimberJiwen

Links
-----
- Docs: https://github.com/MountainClimberJiwen/plc-mcp/tree/main/docs
- Issues: https://github.com/MountainClimberJiwen/plc-mcp/issues
- TIA Openness API: https://support.industry.siemens.com
