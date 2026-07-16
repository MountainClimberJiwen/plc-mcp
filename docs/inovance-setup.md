# 汇川（Inovance）AM600/AC800 适配器使用指南

## 概述

汇川 AM600/AC800 系列 PLC 基于 CODESYS 平台，目前**没有公开的 Openness API**（类似西门子 TIA Portal 的自动化接口）。因此，本适配器采用 **Modbus TCP 协议** 直接读写 PLC 内存变量，将变量映射为虚拟的 "程序块" 供 AI 操作。

## 与西门子适配器的区别

| 功能 | 西门子（TIA Openness） | 汇川（Modbus TCP） |
|------|----------------------|-------------------|
| 读取程序块源码 | 完整 SCL/XML 源码 | 变量实时值（监视表） |
| 写入程序块源码 | 通过 ExternalSource 导入 | 修改变量当前值 |
| 编译 | 支持（编译后自动下载） | **不支持**（需 AutoShop 编译） |
| 列出所有块 | 自动读取项目结构 | 依赖配置文件 |

## 前置要求

1. **PLC 硬件**：汇川 AM600 或 AC800 系列 PLC
2. **网络连接**：PLC 与开发机在同一网络，且已启用 Modbus TCP
3. **Python 依赖**：
   ```bash
   pip install pymodbus>=3.8.0
   ```

## 配置 Modbus TCP

### 1. 在 AutoShop IDE 中启用 Modbus TCP

1. 打开 AutoShop IDE，打开项目
2. 进入 **设备树** -> **PLC 设置** -> **Modbus TCP 服务器**
3. 启用 Modbus TCP Server，设置端口为 **502**（默认）
4. 配置单元 ID（从站地址），通常为 **1**
5. 编译并下载到 PLC

### 2. 确认网络连通性

```bash
# 测试 PLC 是否可达
ping 192.168.1.10

# 测试 Modbus 端口
nc -zv 192.168.1.10 502
```

## 配置变量映射文件

变量映射文件 `config/inovance_blocks.json` 定义了每个 "虚拟块" 的 Modbus 地址映射。

### 文件结构

```json
{
  "blocks": {
    "Motor_Control": {
      "type": "FB",
      "description": "电机控制功能块",
      "variables": [
        {
          "name": "Start_Button",
          "type": "BOOL",
          "section": "VAR_INPUT",
          "address": "X0",
          "default": false,
          "modbus": { "function": 1, "address": 0 }
        },
        {
          "name": "Set_Speed",
          "type": "INT",
          "section": "VAR_INPUT",
          "address": "D0",
          "default": 0,
          "modbus": { "function": 3, "address": 0 }
        }
      ]
    }
  }
}
```

### 字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| `name` | 变量名 | `"Start_Button"` |
| `type` | 数据类型 | `BOOL`, `INT`, `DINT`, `REAL`, `STRING` |
| `section` | 变量区域 | `VAR_INPUT`, `VAR_OUTPUT`, `VAR_IN_OUT`, `VAR` |
| `address` | PLC 内存地址 | `X0`, `Y0`, `D0` |
| `modbus.function` | Modbus 功能码 | `1`（线圈），`3`（保持寄存器） |
| `modbus.address` | Modbus 地址 | `0`, `1`, `2`... |

### 支持的 Modbus 功能码

| 功能码 | 名称 | 说明 |
|--------|------|------|
| `1` | 读线圈（Coils） | 读写布尔值（`0x` 区域） |
| `2` | 读离散输入（Discrete Inputs） | 只读布尔值（`1x` 区域） |
| `3` | 读保持寄存器（Holding Registers） | 读写数值（`4x` 区域） |
| `4` | 读输入寄存器（Input Registers） | 只读数值（`3x` 区域） |

### 支持的数据类型

| 类型 | 寄存器数 | 说明 |
|------|---------|------|
| `BOOL` | 1 | 布尔值（使用线圈/离散输入） |
| `INT` / `SINT` | 1 | 16 位有符号整数 |
| `UINT` / `WORD` | 1 | 16 位无符号整数 |
| `DINT` / `UDINT` / `DWORD` | 2 | 32 位整数（两个寄存器） |
| `REAL` | 2 | 32 位 IEEE 754 浮点数 |
| `STRING` | 16 | 最长 32 字符 ASCII 字符串 |

## 使用方式

### 1. 直接作为 Python 库使用

```python
from plc_vfs import PLCVirtualFS
from plc_vfs.adapters.inovance import InovanceAM600Adapter

# 初始化适配器
adapter = InovanceAM600Adapter(
    host="192.168.1.10",
    port=502,
    block_map_path="config/inovance_blocks.json"
)
adapter.connect()

# 创建 VFS
vfs = PLCVirtualFS(adapter)

# 列出所有块
print(vfs.ls("/devices/PLC_1/blocks"))
# ['Motor_Control.scl', 'Conveyor_Control.scl', 'System_Status.scl']

# 读取块（获取变量实时值）
content = vfs.cat("/devices/PLC_1/blocks/Motor_Control.scl")
print(content)
# // Inovance AM600/AC800 — Modbus Variable Watch
# VAR_INPUT
#   Start_Button : BOOL := FALSE;  // X0 (Modbus read_coils:0)
#   ...

# 修改变量值
new_code = '''// Inovance AM600/AC800 — Modbus Variable Watch
VAR_INPUT
  Start_Button : BOOL := TRUE;
  Set_Speed : INT := 1500;
END_VAR
'''
vfs.echo(new_code, "/devices/PLC_1/blocks/Motor_Control.scl")

# 断开连接
adapter.disconnect()
```

### 2. 使用 Mock 适配器（无需真实 PLC，测试用）

```python
from plc_vfs.adapters.inovance import MockInovanceAdapter
from plc_vfs import PLCVirtualFS

adapter = MockInovanceAdapter(block_map_path="config/inovance_blocks.json")
adapter.connect()

vfs = PLCVirtualFS(adapter)
print(vfs.cat("/devices/PLC_1/blocks/Motor_Control.scl"))
```

### 3. 作为 MCP Server 使用

```bash
# 启动 MCP Server（连接真实 PLC）
python -m plc_tool.server \
    --brand inovance \
    --host 192.168.1.10 \
    --use-vfs

# 或使用 Mock 适配器（无需 PLC）
python -m plc_tool.server \
    --brand mock \
    --use-vfs
```

在 Claude / Cursor 中，AI 可以调用以下 MCP Tools：

| Tool | 功能 | 示例 |
|------|------|------|
| `vfs-ls` | 列出块 | `{"path": "/devices/PLC_1/blocks"}` |
| `vfs-cat` | 读取变量值 | `{"path": "/devices/PLC_1/blocks/Motor_Control.scl"}` |
| `vfs-write` | 修改变量值 | `{"path": "...", "content": "..."}` |
| `vfs-diff` | 比较两个块 | `{"path_a": "...", "path_b": "..."}` |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `INOVANCE_PLC_HOST` | PLC IP 地址 | `192.168.1.10` |
| `PLC_MCP_USE_VFS` | 启用 VFS | `0`（`1` 启用） |
| `PLC_MCP_BRAND` | 品牌选择（计划中） | `siemens` |

## 注意事项

1. **Modbus 不支持编译**：`compile()` 操作会返回错误。修改程序块源码后，必须使用 **AutoShop IDE** 或 **CODESYS** 编译并下载到 PLC。

2. **地址映射需要手动配置**：`inovance_blocks.json` 中的 Modbus 地址必须与 AutoShop 中的变量地址一一对应。建议在 AutoShop 中导出符号表（Symbol Table）后自动生成此文件。

3. **BOOL 变量使用线圈（Function 1）**：在 Modbus 中，布尔变量（BOOL）应映射到线圈（Function 1），而数值变量应映射到保持寄存器（Function 3）。不要混用。

4. **并发访问**：Modbus 是单线程协议，不要同时从多个客户端向同一个 PLC 发起大量读写请求。

5. **地址冲突**：确保不同变量使用的 Modbus 地址不重叠。例如，一个 `REAL` 类型占 2 个寄存器，地址为 `D2` 和 `D3`。

## 故障排查

### 连接失败

```
ConnectionException: 无法连接到汇川 PLC 192.168.1.10:502
```

- 检查 PLC 电源和网络连接
- 确认 AutoShop 中已启用 Modbus TCP Server
- 确认防火墙允许端口 502 的通信
- 尝试 `ping 192.168.1.10` 和 `telnet 192.168.1.10 502`

### 块不存在

```
FileNotFoundError: 块 'Motor_Control' 未在映射文件中找到
```

- 检查 `config/inovance_blocks.json` 中是否定义了该块
- 检查文件路径是否正确
- 使用 `vfs.ls("/devices/PLC_1/blocks")` 查看可用块

### 变量值未更新

- 确认 Modbus 地址与 PLC 中的变量地址一致
- 确认变量类型与 Modbus 功能码匹配（BOOL->Function 1，数值->Function 3）
- 检查 PLC 是否处于 RUN 状态
- 使用 `adapter.is_connected()` 确认连接状态

## 未来扩展

1. **CODESYS 项目文件解析**：直接解析 `.project` 文件（ZIP 格式），提取程序块源码和变量符号表，实现 "真正" 的块源码读写能力。

2. **OPC UA 适配器**：AM600/AC800 支持 OPC UA 服务器，可提供更丰富的数据模型（变量名、数据类型、程序组织结构），作为 Modbus 的升级方案。

3. **自动符号表导出**：从 AutoShop IDE 自动导出符号表（Symbol Table），生成 `inovance_blocks.json` 配置文件，省去手动配置。

## 相关链接

- [汇川官网](https://www.inovance.com)
- [pymodbus 文档](https://pymodbus.readthedocs.io/)
- [CODESYS 文档](https://content.helpme-codesys.com/)
- [Modbus 协议规范](https://modbus.org/specs.php)
