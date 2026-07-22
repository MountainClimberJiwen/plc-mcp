"""
汇川（Inovance）AM600/AC800 系列 PLC 适配器

通过 Modbus TCP 协议直接读写 PLC 内存变量，
将变量映射为虚拟的 PLC 块，供 AI Agent 通过 VFS 操作。

技术栈：
- 通信协议：Modbus TCP (pymodbus)
- 地址映射：CODESYS 标准 Modbus 映射
- 支持类型：BOOL, INT, DINT, REAL, STRING

已知限制：
- 无法直接读取/写入程序块（FB/FC/POU）源码
- 不支持编译操作（需要 AutoShop IDE 编译并下载）
- 变量映射需要手动配置 JSON 文件

示例：
    adapter = InovanceAM600Adapter(
        host="192.168.1.10",
        port=502,
        block_map_path="config/inovance_blocks.json"
    )
    adapter.connect()
    block = adapter.read_block("Motor_Control")
    print(block.source_code)  # 变量监视值

作者：MountainClimberJiwen
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from ..core import PLCBlock
from .base import PLCAdapter


try:
    from pymodbus.client import ModbusTcpClient
    from pymodbus.exceptions import ModbusException, ConnectionException
except ImportError:
    ModbusTcpClient = None
    ModbusException = Exception
    ConnectionException = Exception


class InovanceAM600Adapter(PLCAdapter):
    """
    汇川 AM600/AC800 系列 PLC 适配器

    通过 Modbus TCP 协议与 PLC 通信，
    将 PLC 中的变量映射为虚拟的 "程序块" 供 AI 操作。
    """

    # Modbus 功能码映射
    MODBUS_FUNCTION_MAP = {
        1:  "read_coils",           # 0x    读写线圈
        2:  "read_discrete_inputs", # 1x    读离散输入
        3:  "read_holding_registers", # 4x  读写保持寄存器
        4:  "read_input_registers",   # 3x  读输入寄存器
    }

    # CODESYS 变量类型 -> 寄存器数量映射
    TYPE_SIZE_MAP = {
        "BOOL":  1,
        "BYTE":  1,
        "WORD":  1,
        "DWORD": 2,
        "SINT":  1,
        "INT":   1,
        "DINT":  2,
        "USINT": 1,
        "UINT":  1,
        "UDINT": 2,
        "REAL":  2,
        "LREAL": 4,
        "STRING": 16,  # 32 字节字符串 (16 个寄存器)
    }

    def __init__(
        self,
        host: str = "192.168.1.10",
        port: int = 502,
        unit_id: int = 1,
        block_map_path: Optional[str] = None,
        timeout: float = 5.0,
    ):
        """
        初始化汇川适配器

        Args:
            host: PLC 的 IP 地址
            port: Modbus TCP 端口（默认 502）
            unit_id: Modbus 从站地址（默认 1）
            block_map_path: 变量映射 JSON 文件路径
            timeout: 连接超时（秒）
        """
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self._client: Optional[ModbusTcpClient] = None
        self._block_map: Dict[str, Any] = {}

        # 加载变量映射配置
        if block_map_path and os.path.exists(block_map_path):
            self._load_block_map(block_map_path)
        elif block_map_path:
            self._block_map_path = block_map_path
        else:
            self._block_map_path = None

    # === 适配器接口实现 ===

    @property
    def brand(self) -> str:
        return "inovance"

    def connect(self):
        """建立 Modbus TCP 连接"""
        if ModbusTcpClient is None:
            raise ImportError(
                "pymodbus is required. Install with: pip install pymodbus>=3.8.0"
            )

        self._client = ModbusTcpClient(
            host=self.host,
            port=self.port,
            timeout=self.timeout,
        )
        if not self._client.connect():
            raise ConnectionException(
                f"无法连接到汇川 PLC {self.host}:{self.port}"
            )
        return True

    def disconnect(self):
        """断开 Modbus TCP 连接"""
        if self._client:
            self._client.close()
            self._client = None

    def read_block(self, block_name: str) -> PLCBlock:
        """
        读取 "程序块"（实际上是变量组的当前值）

        从 block_map 中查找变量定义，通过 Modbus 读取寄存器，
        返回格式化的变量监视表文本。
        """
        block_def = self._get_block_definition(block_name)
        if not block_def:
            raise FileNotFoundError(
                f"块 '{block_name}' 未在映射文件中找到。"
                f"可用块: {self.list_blocks()}"
            )

        variables = block_def.get("variables", [])
        read_values = self._read_variables(variables)

        # 格式化为类似 SCL/结构化文本的变量监视表
        source_code = self._format_block_watch(
            block_name,
            block_def.get("type", "FB"),
            variables,
            read_values,
        )

        return PLCBlock(
            name=block_name,
            block_type=block_def.get("type", "FB"),
            language="ST",  # CODESYS 使用结构化文本
            source_code=source_code,
            metadata={
                "brand": "inovance",
                "series": "AM600/AC800",
                "protocol": "Modbus TCP",
                "read_at": datetime.now().isoformat(),
                "variables": variables,
                "values": read_values,
            }
        )

    def write_block(self, block: PLCBlock) -> bool:
        """
        写入 "程序块"（实际上是修改变量的当前值）

        解析 source_code 中的变量值，通过 Modbus 写入寄存器。
        """
        block_def = self._get_block_definition(block.name)
        if not block_def:
            raise FileNotFoundError(f"块 '{block.name}' 未在映射文件中找到")

        variables = block_def.get("variables", [])
        new_values = self._parse_values_from_source(block.source_code, variables)

        return self._write_variables(variables, new_values)

    def list_blocks(self) -> List[str]:
        """列出所有已配置的块名称"""
        return list(self._block_map.get("blocks", {}).keys())

    def compile(self) -> Dict[str, Any]:
        """
        编译项目

        ⚠️ Modbus 协议不支持编译操作。
        需要使用 AutoShop IDE 或 CODESYS 手动编译并下载到 PLC。
        """
        return {
            "success": False,
            "warnings": 0,
            "errors": 1,
            "message": (
                "Modbus 协议不支持编译操作。"
                "请使用 AutoShop IDE 或 CODESYS 编译并下载到 PLC。"
            ),
        }

    # === Modbus 读写核心 ===

    def _read_variables(self, variables: List[Dict]) -> Dict[str, Any]:
        """
        批量读取变量值

        按 Modbus 功能码分组，合并读取请求以提高效率。
        """
        if not self._client or not self._client.connected:
            raise ConnectionException("Modbus 未连接")

        # 按功能码分组
        groups: Dict[int, List[Tuple[str, int, int]]] = {}
        for var in variables:
            func = var["modbus"]["function"]
            addr = var["modbus"]["address"]
            size = self.TYPE_SIZE_MAP.get(var["type"], 1)
            if func not in groups:
                groups[func] = []
            groups[func].append((var["name"], addr, size))

        values = {}

        for func_code, var_list in groups.items():
            if func_code in (1, 2):  # 线圈 / 离散输入
                for name, addr, size in var_list:
                    result = self._client.read_coils(
                        address=addr, count=1, slave=self.unit_id
                    )
                    if result and not result.isError():
                        values[name] = result.bits[0]
                    else:
                        values[name] = None

            elif func_code in (3, 4):  # 保持寄存器 / 输入寄存器
                # 读取连续的寄存器块
                var_list_sorted = sorted(var_list, key=lambda x: x[1])
                for name, addr, size in var_list_sorted:
                    if func_code == 3:
                        result = self._client.read_holding_registers(
                            address=addr, count=size, slave=self.unit_id
                        )
                    else:
                        result = self._client.read_input_registers(
                            address=addr, count=size, slave=self.unit_id
                        )

                    if result and not result.isError():
                        registers = result.registers
                        values[name] = self._registers_to_value(
                            registers, var["type"]
                        )
                    else:
                        values[name] = None

        return values

    def _write_variables(self, variables: List[Dict], new_values: Dict[str, Any]) -> bool:
        """批量写入变量值"""
        if not self._client or not self._client.connected:
            raise ConnectionException("Modbus 未连接")

        for var in variables:
            name = var["name"]
            if name not in new_values:
                continue

            func = var["modbus"]["function"]
            addr = var["modbus"]["address"]
            value = new_values[name]

            if func == 1:  # 线圈写入
                result = self._client.write_coil(
                    address=addr, value=bool(value), slave=self.unit_id
                )
            elif func == 3:  # 保持寄存器写入
                registers = self._value_to_registers(value, var["type"])
                if len(registers) == 1:
                    result = self._client.write_register(
                        address=addr, value=registers[0], slave=self.unit_id
                    )
                else:
                    result = self._client.write_registers(
                        address=addr, values=registers, slave=self.unit_id
                    )
            else:
                # 只读区域（离散输入、输入寄存器）不支持写入
                continue

            if result and result.isError():
                return False

        return True

    # === 数据格式转换 ===

    def _registers_to_value(self, registers: List[int], var_type: str) -> Any:
        """将 Modbus 寄存器值转换为 Python 类型"""
        if var_type == "BOOL":
            return bool(registers[0])

        elif var_type in ("INT", "SINT"):
            # 有符号 16 位整数
            val = registers[0]
            if val >= 0x8000:
                val -= 0x10000
            return val

        elif var_type in ("DINT", "UDINT"):
            # 32 位整数（两个寄存器，高字节在前）
            high = registers[0]
            low = registers[1] if len(registers) > 1 else 0
            val = (high << 16) | low
            if var_type == "DINT" and val >= 0x80000000:
                val -= 0x100000000
            return val

        elif var_type == "REAL":
            # 32 位浮点数（IEEE 754）
            import struct
            high = registers[0]
            low = registers[1] if len(registers) > 1 else 0
            raw = (high << 16) | low
            return struct.unpack('>f', struct.pack('>I', raw))[0]

        elif var_type == "STRING":
            # 字符串（寄存器数组，每寄存器 2 个 ASCII 字符）
            chars = []
            for reg in registers:
                chars.append(chr((reg >> 8) & 0xFF))
                chars.append(chr(reg & 0xFF))
            return ''.join(chars).rstrip('\x00')

        else:
            return registers[0]  # 默认返回原始值

    def _value_to_registers(self, value: Any, var_type: str) -> List[int]:
        """将 Python 类型转换为 Modbus 寄存器值"""
        if var_type == "BOOL":
            return [1 if value else 0]

        elif var_type in ("INT", "SINT", "WORD", "UINT"):
            return [int(value) & 0xFFFF]

        elif var_type in ("DINT", "UDINT", "DWORD"):
            val = int(value) & 0xFFFFFFFF
            return [(val >> 16) & 0xFFFF, val & 0xFFFF]

        elif var_type == "REAL":
            import struct
            raw = struct.unpack('>I', struct.pack('>f', float(value)))[0]
            return [(raw >> 16) & 0xFFFF, raw & 0xFFFF]

        elif var_type == "STRING":
            s = str(value).encode('ascii')[:32]
            # 补齐到偶数字节
            if len(s) % 2 != 0:
                s += b'\x00'
            registers = []
            for i in range(0, len(s), 2):
                registers.append((s[i] << 8) | s[i + 1])
            # 补齐到 16 个寄存器
            while len(registers) < 16:
                registers.append(0)
            return registers[:16]

        else:
            return [int(value) & 0xFFFF]

    # === 文本格式化与解析 ===

    def _format_block_watch(
        self,
        block_name: str,
        block_type: str,
        variables: List[Dict],
        values: Dict[str, Any],
    ) -> str:
        """将变量值格式化为类似 ST 的监视表文本"""
        lines = [
            f'// Inovance AM600/AC800 — Modbus Variable Watch',
            f'// Block: {block_name} ({block_type})',
            f'// Read at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'// Protocol: Modbus TCP ({self.host}:{self.port})',
            f'',
        ]

        # 按变量区域分组
        sections = {
            "VAR_INPUT": [],
            "VAR_OUTPUT": [],
            "VAR_IN_OUT": [],
            "VAR": [],
        }

        for var in variables:
            section = var.get("section", "VAR")
            if section not in sections:
                section = "VAR"
            sections[section].append(var)

        for section_name, vars_in_section in sections.items():
            if not vars_in_section:
                continue

            lines.append(f'{section_name}')
            for var in vars_in_section:
                name = var["name"]
                var_type = var["type"]
                value = values.get(name, "???")
                address = var.get("address", "?")
                modbus_func = var["modbus"]["function"]
                modbus_addr = var["modbus"]["address"]
                func_str = self.MODBUS_FUNCTION_MAP.get(modbus_func, str(modbus_func))

                # 格式化值
                if var_type == "REAL" and isinstance(value, float):
                    val_str = f"{value:.4f}"
                elif var_type == "BOOL":
                    val_str = "TRUE" if value else "FALSE"
                else:
                    val_str = str(value)

                lines.append(
                    f'  {name} : {var_type} := {val_str};  '
                    f'// {address} (Modbus {func_str}:{modbus_addr})'
                )

            lines.append('END_VAR')
            lines.append('')

        # 添加注释说明
        lines.append('// ─────────────────────────────────────')
        lines.append('// 提示：这是变量的实时监视值，不是源码。')
        lines.append('// 修改值后调用 write_block 可通过 Modbus 写入 PLC。')
        lines.append('// 程序块源码修改请使用 AutoShop IDE 或 CODESYS。')
        lines.append('')

        return '\n'.join(lines)

    def _parse_values_from_source(
        self, source_code: str, variables: List[Dict]
    ) -> Dict[str, Any]:
        """从文本中解析变量值（简化实现）"""
        values = {}
        import re

        for var in variables:
            name = var["name"]
            var_type = var["type"]
            # 匹配:  VarName : TYPE := value;
            pattern = rf'{name}\s*:\s*{var_type}\s*:=\s*([^;]+);'
            match = re.search(pattern, source_code, re.IGNORECASE)
            if match:
                raw = match.group(1).strip()
                values[name] = self._parse_value(raw, var_type)

        return values

    def _parse_value(self, raw: str, var_type: str) -> Any:
        """将字符串值解析为正确的 Python 类型"""
        raw = raw.strip()

        if var_type == "BOOL":
            return raw.upper() in ("TRUE", "1", "ON", "YES")

        elif var_type == "REAL":
            try:
                return float(raw)
            except ValueError:
                return 0.0

        elif var_type in ("DINT", "UDINT"):
            try:
                return int(raw)
            except ValueError:
                return 0

        elif var_type == "STRING":
            # 去除引号
            if (raw.startswith('"') and raw.endswith('"')) or \
               (raw.startswith("'") and raw.endswith("'")):
                return raw[1:-1]
            return raw

        else:  # INT, SINT, WORD, UINT, etc.
            try:
                return int(raw)
            except ValueError:
                return 0

    # === 配置管理 ===

    def _load_block_map(self, path: str):
        """加载变量映射配置文件"""
        with open(path, 'r', encoding='utf-8') as f:
            self._block_map = json.load(f)
        self._block_map_path = path

    def _get_block_definition(self, block_name: str) -> Optional[Dict]:
        """获取块定义"""
        return self._block_map.get("blocks", {}).get(block_name)

    def reload_block_map(self, path: Optional[str] = None):
        """重新加载块映射（支持热更新）"""
        if path:
            self._load_block_map(path)
        elif self._block_map_path:
            self._load_block_map(self._block_map_path)

    def save_block_map(self, path: Optional[str] = None):
        """保存当前块映射到文件"""
        save_path = path or self._block_map_path
        if not save_path:
            raise ValueError("未指定保存路径")
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(self._block_map, f, indent=2, ensure_ascii=False)

    def add_block_definition(self, block_name: str, block_def: Dict):
        """动态添加块定义（无需编辑 JSON 文件）"""
        if "blocks" not in self._block_map:
            self._block_map["blocks"] = {}
        self._block_map["blocks"][block_name] = block_def

    # === 状态与诊断 ===

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._client is not None and self._client.connected

    def __repr__(self) -> str:
        status = "connected" if self.is_connected() else "disconnected"
        return (
            f"InovanceAM600Adapter("
            f"{self.host}:{self.port}, "
            f"status={status}, "
            f"blocks={len(self.list_blocks())}"
            f")"
        )


class MockInovanceAdapter(InovanceAM600Adapter):
    """
    Mock 汇川适配器（用于测试，无需真实 PLC）

    使用本地内存模拟 Modbus 寄存器，
    支持完整的适配器接口，无需网络连接。
    """

    def __init__(self, block_map_path: Optional[str] = None):
        # 不调用父类 __init__，避免网络相关设置
        self.host = "localhost"
        self.port = 502
        self.unit_id = 1
        self.timeout = 5.0
        self._block_map: Dict[str, Any] = {}
        self._block_map_path = None
        self._mock_registers: Dict[int, Dict[int, int]] = {
            1: {},   # 线圈 (coils)
            3: {},   # 保持寄存器 (holding registers)
        }
        self._mock_connected = False

        if block_map_path and os.path.exists(block_map_path):
            self._load_block_map(block_map_path)

    def connect(self):
        """模拟连接"""
        self._mock_connected = True
        # 初始化模拟寄存器默认值
        self._init_mock_registers()
        return True

    def disconnect(self):
        """模拟断开"""
        self._mock_connected = False

    def is_connected(self) -> bool:
        return self._mock_connected

    def _init_mock_registers(self):
        """根据块映射初始化模拟寄存器"""
        for block_name, block_def in self._block_map.get("blocks", {}).items():
            for var in block_def.get("variables", []):
                func = var["modbus"]["function"]
                addr = var["modbus"]["address"]
                default = var.get("default", 0)

                if func == 1:  # 线圈
                    self._mock_registers[1][addr] = 1 if default else 0
                elif func == 3:  # 保持寄存器
                    size = self.TYPE_SIZE_MAP.get(var["type"], 1)
                    regs = self._value_to_registers(default, var["type"])
                    for i, reg in enumerate(regs):
                        self._mock_registers[3][addr + i] = reg

    def _read_variables(self, variables: List[Dict]) -> Dict[str, Any]:
        """从模拟寄存器读取"""
        if not self._mock_connected:
            raise ConnectionException("Mock 连接未建立")

        values = {}
        for var in variables:
            name = var["name"]
            func = var["modbus"]["function"]
            addr = var["modbus"]["address"]
            size = self.TYPE_SIZE_MAP.get(var["type"], 1)

            if func == 1:  # 线圈
                val = bool(self._mock_registers[1].get(addr, 0))
                values[name] = val

            elif func in (3, 4):  # 寄存器
                regs = [
                    self._mock_registers[3].get(addr + i, 0)
                    for i in range(size)
                ]
                values[name] = self._registers_to_value(regs, var["type"])

        return values

    def _write_variables(self, variables: List[Dict], new_values: Dict[str, Any]) -> bool:
        """写入模拟寄存器"""
        if not self._mock_connected:
            raise ConnectionException("Mock 连接未建立")

        for var in variables:
            name = var["name"]
            if name not in new_values:
                continue

            func = var["modbus"]["function"]
            addr = var["modbus"]["address"]
            value = new_values[name]

            if func == 1:  # 线圈
                self._mock_registers[1][addr] = 1 if value else 0

            elif func == 3:  # 保持寄存器
                regs = self._value_to_registers(value, var["type"])
                for i, reg in enumerate(regs):
                    self._mock_registers[3][addr + i] = reg

        return True
