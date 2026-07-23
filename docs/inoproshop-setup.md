# 汇川 InoProShop 适配器使用指南

## 概述

汇川 **InoProShop** 是基于 CODESYS 平台的中型 PLC 编程软件。与西门子 TIA Portal 不同，InoProShop 没有公开的 COM/Openness API，但它内置了 **IronPython 脚本引擎**，可以通过 `InoProShop.exe --runscript=<script.py>` 的方式自动化操作项目。

本适配器 **用 Python 原生实现** 了这一机制，直接生成 IronPython 脚本并启动 InoProShop 执行，从而：

- 不再依赖外部的 Node.js `InoProShop_LIMIT_MCP` bundle
- 与 TIA Portal 适配器保持同样的 `PLCAdapter` 抽象结构
- 支持通过 `PLCVirtualFS` 和 MCP Server 统一接口读写程序块

## 前置要求

| 依赖 | 版本/说明 |
|------|----------|
| 操作系统 | Windows（InoProShop 仅支持 Windows） |
| InoProShop | V1.9.x（SP11 内核） |
| Python | >= 3.10 |
| 项目文件 | 已有的 `.project` 文件，或允许自动创建的目录 |

## 适配器架构

```
plc_tool/server.py  (MCP Server)
    └── PLCVirtualFS
            └── InoProShopAdapter  (PLCAdapter 实现)
                    ├── InoProShopScriptRunner
                    │       └── spawns InoProShop.exe --runscript=...
                    └── inoproshop_scripts
                            └── 生成 IronPython 脚本模板
```

这与 `SiemensTIAAdapter` 的结构对称：TIA 适配器直接调用 TIA Openness API，InoProShop 适配器则直接调用 CODESYS IronPython 脚本引擎。

## 环境变量

启动 MCP Server 时通过环境变量配置：

| 变量 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `PLC_MCP_BRAND` | 是 | 固定填 `inoproshop` | `inoproshop` |
| `INOPROSHOP_PROJECT_PATH` | 是 | `.project` 文件完整路径 | `C:/Projects/my_plc.project` |
| `INOPROSHOP_CODESYS_PATH` | 是 | InoProShop.exe 完整路径 | `D:/Inovance Control/.../InoProShop.exe` |
| `INOPROSHOP_PROFILE` | 否 | CODESYS profile 名称 | `InoProShop(V1.9.0.1)` |
| `INOPROSHOP_WORKSPACE` | 否 | 工作目录，默认取项目所在目录 | `C:/Projects` |
| `INOPROSHOP_TIMEOUT` | 否 | 单次脚本执行超时（秒） | `300` |

## 快速开始

### 1. 作为 Python 库使用

```python
from plc_vfs import PLCVirtualFS
from plc_vfs.adapters.inoproshop import InoProShopAdapter

adapter = InoProShopAdapter(
    project_path="C:/Projects/my_plc.project",
    codesys_path="D:/Inovance Control/InoProShop/CODESYS/Common/InoProShop.exe",
    profile="InoProShop(V1.9.0.1)",
)
adapter.connect()

vfs = PLCVirtualFS(adapter)

# 列出所有 POU
print(vfs.ls("/devices/PLC_1/blocks"))

# 读取 Main POU
print(vfs.cat("/devices/PLC_1/blocks/Main.scl"))

# 写入新代码
vfs.echo('''PROGRAM Main
VAR
    counter : INT;
END_VAR

counter := counter + 1;
END_PROGRAM
''', "/devices/PLC_1/blocks/Main.scl")

# 编译
print(adapter.compile())
```

### 2. 作为 MCP Server 使用

```bash
export PLC_MCP_BRAND=inoproshop
export INOPROSHOP_PROJECT_PATH="C:/Projects/my_plc.project"
export INOPROSHOP_CODESYS_PATH="D:/Inovance Control/InoProShop/CODESYS/Common/InoProShop.exe"
export INOPROSHOP_PROFILE="InoProShop(V1.9.0.1)"

python -m plc_tool.server
```

在 Claude / Cursor 中配置 MCP Server：

```json
{
  "mcpServers": {
    "inoproshop": {
      "command": "python",
      "args": ["-m", "plc_tool.server"],
      "env": {
        "PLC_MCP_BRAND": "inoproshop",
        "INOPROSHOP_PROJECT_PATH": "C:/Projects/my_plc.project",
        "INOPROSHOP_CODESYS_PATH": "D:/Inovance Control/InoProShop/CODESYS/Common/InoProShop.exe",
        "INOPROSHOP_PROFILE": "InoProShop(V1.9.0.1)"
      }
    }
  }
}
```

### 3. 使用 Mock 适配器（无需 Windows，测试用）

```python
from plc_vfs.adapters.inoproshop import MockInoProShopAdapter
from plc_vfs import PLCVirtualFS

adapter = MockInoProShopAdapter()
adapter.connect()

vfs = PLCVirtualFS(adapter)
print(vfs.cat("/devices/PLC_1/blocks/Main.scl"))
```

## MCP Tools

通过 `plc_tool.server` 暴露的工具与 TIA / Inovance 等品牌一致：

| Tool | 功能 | 示例 |
|------|------|------|
| `vfs_ls` | 列出目录/块 | `{"path": "/devices/PLC_1/blocks"}` |
| `vfs_cat` | 读取 POU 源码 | `{"path": "/devices/PLC_1/blocks/Main.scl"}` |
| `vfs_write` | 写入 POU 源码 | `{"path": "...", "content": "..."}` |
| `vfs_diff` | 比较两个块 | `{"path_a": "...", "path_b": "..."}` |
| `vfs_grep` | 搜索字符串 | `{"pattern": "Motor", "path": "..."}` |
| `vfs_compile` | 编译项目 | `{}` |

## 自动创建项目

如果 `INOPROSHOP_PROJECT_PATH` 指向的文件不存在，适配器会尝试：

1. 在 `INOPROSHOP_CODESYS_PATH` 同级目录查找 `Templates/Standard.project`
2. 在 `ProgramData/CODESYS/CODESYS/<profile>/Templates/Standard.project` 查找
3. 在 `ProgramData/CODESYS/Templates/Standard.project` 查找

找到模板后复制到目标路径并打开。如果找不到模板，会抛出错误。

## 调试技巧

### 查看最后一次执行的 IronPython 脚本

默认情况下，执行器会把最后一次脚本复制到：

```
%TEMP%/codesys_last_script.py
```

可以直接打开查看生成的脚本内容，排查语法或对象模型问题。

### 使用 probe_api 探查 CODESYS 对象模型

```python
from plc_vfs.adapters.inoproshop_script_runner import InoProShopScriptRunner

runner = InoProShopScriptRunner(
    codesys_path=".../InoProShop.exe",
    profile="InoProShop(V1.9.0.1)",
)

# 列出 primary project 的所有属性和方法
result = runner.probe_api("dir")
print(result["output"])

# 列出项目根节点的子对象
result = runner.probe_api("children")
print(result["output"])

# 执行自定义 IronPython 代码
result = runner.probe_api(
    "custom",
    custom_code='rlog("project name: " + probe_obj.name)',
)
print(result["output"])
```

## 已知限制

以下功能受限于 CODESYS SP11 脚本 API，暂时无法通过本适配器实现：

- 向 Task 自动添加 / 删除 POU 调用
- IO 通道变量映射
- EtherCAT PDO 映射配置

新建 POU 后，通常需要手动在 InoProShop 中把它挂到 Task 上，或调用 `Main` 等已有 Task 中的 POU。

## 故障排查

### Permission denied: InoProShop.exe

确保 `INOPROSHOP_CODESYS_PATH` 指向的是可执行文件本身，而不是目录。

### 找不到 Standard.project 模板

检查 `ProgramData/CODESYS/.../Templates/` 目录是否存在。如果 InoProShop 安装路径非标准，可先手动创建一个空项目，再让 AI 在此基础上工作。

### SCRIPT_ERROR: POU not found

CODESYS 不同版本的项目结构可能不同（例如 POU 是否直接挂在 `Application` 下）。可用 `probe_api("children")` 查看实际结构，然后调整脚本模板中的路径查找逻辑。

### 编译返回成功但运行时出错

这是 CODESYS 常见行为，例如：

- `MC_MoveAbsolute` 等指令的 `Execute` 必须配合 `R_TRIG` 使用脉冲触发
- `Acceleration` / `Deceleration` 必须大于 0
- 轴对象 `AXIS_REF_SM3` 在功能块间传递必须使用 `VAR_IN_OUT`

## 相关文件

- `src/plc_vfs/adapters/inoproshop.py` — 适配器主实现
- `src/plc_vfs/adapters/inoproshop_script_runner.py` — CODESYS 脚本执行器
- `src/plc_vfs/adapters/inoproshop_scripts.py` — IronPython 脚本模板
- `tests/test_inoproshop_adapter.py` — 单元测试
