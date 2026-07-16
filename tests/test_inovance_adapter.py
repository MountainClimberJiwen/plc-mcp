"""
汇川（Inovance）AM600/AC800 适配器单元测试

测试范围：
- MockInovanceAdapter（无需真实 PLC，纯本地内存测试）
- InovanceAM600Adapter 的数据格式转换方法
- VFS 集成测试

运行方式：
    pytest tests/test_inovance_adapter.py -v

作者：MountainClimberJiwen
"""

import os
import sys
import json
import tempfile
import pytest
from unittest.mock import Mock, MagicMock, patch

# 确保能导入项目源码
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from plc_vfs.adapters.inovance import InovanceAM600Adapter, MockInovanceAdapter
from plc_vfs.core import PLCVirtualFS, PLCBlock


# === Fixtures ===

@pytest.fixture
def sample_block_map():
    """返回测试用的块映射配置"""
    return {
        "blocks": {
            "Motor_Control": {
                "type": "FB",
                "variables": [
                    {
                        "name": "Start_Button",
                        "type": "BOOL",
                        "section": "VAR_INPUT",
                        "address": "X0",
                        "default": False,
                        "modbus": {"function": 1, "address": 0}
                    },
                    {
                        "name": "Motor_On",
                        "type": "BOOL",
                        "section": "VAR_OUTPUT",
                        "address": "Y0",
                        "default": False,
                        "modbus": {"function": 1, "address": 10}
                    },
                    {
                        "name": "Set_Speed",
                        "type": "INT",
                        "section": "VAR_INPUT",
                        "address": "D0",
                        "default": 0,
                        "modbus": {"function": 3, "address": 0}
                    },
                    {
                        "name": "Motor_Current",
                        "type": "REAL",
                        "section": "VAR_OUTPUT",
                        "address": "D2",
                        "default": 0.0,
                        "modbus": {"function": 3, "address": 2}
                    },
                ]
            },
            "System_Status": {
                "type": "FB",
                "variables": [
                    {
                        "name": "System_Ready",
                        "type": "BOOL",
                        "section": "VAR_OUTPUT",
                        "address": "Y20",
                        "default": True,
                        "modbus": {"function": 1, "address": 40}
                    },
                    {
                        "name": "Alarm_Code",
                        "type": "INT",
                        "section": "VAR_OUTPUT",
                        "address": "D20",
                        "default": 0,
                        "modbus": {"function": 3, "address": 20}
                    },
                ]
            }
        }
    }


@pytest.fixture
def block_map_file(sample_block_map):
    """创建临时块映射文件"""
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(sample_block_map, f)
    yield path
    os.unlink(path)


@pytest.fixture
def mock_adapter(block_map_file):
    """创建已连接的 MockInovanceAdapter"""
    adapter = MockInovanceAdapter(block_map_path=block_map_file)
    adapter.connect()
    yield adapter
    adapter.disconnect()


# === MockInovanceAdapter 测试 ===

class TestMockInovanceAdapter:
    """测试 MockInovanceAdapter（无需网络）"""

    def test_connect(self, block_map_file):
        """测试连接"""
        adapter = MockInovanceAdapter(block_map_path=block_map_file)
        assert not adapter.is_connected()
        adapter.connect()
        assert adapter.is_connected()
        adapter.disconnect()
        assert not adapter.is_connected()

    def test_brand(self, block_map_file):
        """测试品牌标识"""
        adapter = MockInovanceAdapter(block_map_path=block_map_file)
        assert adapter.brand == "inovance"

    def test_list_blocks(self, mock_adapter):
        """测试列出块"""
        blocks = mock_adapter.list_blocks()
        assert isinstance(blocks, list)
        assert "Motor_Control" in blocks
        assert "System_Status" in blocks

    def test_block_exists(self, mock_adapter):
        """测试块存在检查"""
        assert mock_adapter.block_exists("Motor_Control")
        assert not mock_adapter.block_exists("NonExistent")

    def test_read_block(self, mock_adapter):
        """测试读取块"""
        block = mock_adapter.read_block("Motor_Control")
        assert isinstance(block, PLCBlock)
        assert block.name == "Motor_Control"
        assert block.block_type == "FB"
        assert block.language == "ST"
        assert block.source_code is not None
        # 检查内容包含变量
        assert "Start_Button" in block.source_code
        assert "Motor_On" in block.source_code
        assert "Set_Speed" in block.source_code

    def test_read_block_metadata(self, mock_adapter):
        """测试读取块的元数据"""
        block = mock_adapter.read_block("Motor_Control")
        assert block.metadata["brand"] == "inovance"
        assert block.metadata["series"] == "AM600/AC800"
        assert block.metadata["protocol"] == "Modbus TCP"
        assert "read_at" in block.metadata

    def test_read_block_not_found(self, mock_adapter):
        """测试读取不存在的块"""
        with pytest.raises(FileNotFoundError):
            mock_adapter.read_block("NonExistent")

    def test_write_block(self, mock_adapter):
        """测试写入块（修改变量值）"""
        new_code = '''// Inovance AM600/AC800 — Modbus Variable Watch
VAR_INPUT
  Start_Button : BOOL := TRUE;
  Set_Speed : INT := 1500;
END_VAR
VAR_OUTPUT
  Motor_On : BOOL := TRUE;
  Motor_Current : REAL := 12.5;
END_VAR
'''
        block = PLCBlock(name="Motor_Control", source_code=new_code)
        result = mock_adapter.write_block(block)
        assert result is True

        # 验证写入后的值
        read_back = mock_adapter.read_block("Motor_Control")
        assert "Start_Button : BOOL := TRUE" in read_back.source_code
        assert "Set_Speed : INT := 1500" in read_back.source_code
        assert "Motor_Current : REAL := 12.5000" in read_back.source_code

    def test_compile_not_supported(self, mock_adapter):
        """测试编译不支持"""
        result = mock_adapter.compile()
        assert result["success"] is False
        assert result["errors"] == 1
        assert "Modbus" in result["message"]

    def test_repr(self, mock_adapter):
        """测试字符串表示"""
        repr_str = repr(mock_adapter)
        assert "InovanceAM600Adapter" in repr_str
        assert "connected" in repr_str


# === 数据格式转换测试 ===

class TestDataFormatConversion:
    """测试寄存器与 Python 值之间的转换"""

    def test_bool_conversion(self, mock_adapter):
        """测试 BOOL 转换"""
        adapter = mock_adapter
        assert adapter._registers_to_value([0], "BOOL") is False
        assert adapter._registers_to_value([1], "BOOL") is True
        assert adapter._value_to_registers(False, "BOOL") == [0]
        assert adapter._value_to_registers(True, "BOOL") == [1]

    def test_int_conversion(self, mock_adapter):
        """测试 INT 转换"""
        adapter = mock_adapter
        assert adapter._registers_to_value([100], "INT") == 100
        assert adapter._registers_to_value([0xFFFF], "INT") == -1  # 有符号
        assert adapter._value_to_registers(100, "INT") == [100]
        assert adapter._value_to_registers(-1, "INT") == [0xFFFF]

    def test_dint_conversion(self, mock_adapter):
        """测试 DINT 转换"""
        adapter = mock_adapter
        assert adapter._registers_to_value([0, 100], "DINT") == 100
        assert adapter._registers_to_value([0x7FFF, 0xFFFF], "DINT") == 2147483647
        assert adapter._value_to_registers(100, "DINT") == [0, 100]
        assert adapter._value_to_registers(65536, "DINT") == [1, 0]

    def test_real_conversion(self, mock_adapter):
        """测试 REAL 转换"""
        adapter = mock_adapter
        import struct
        # IEEE 754: 3.14 的大端表示
        raw = struct.unpack('>I', struct.pack('>f', 3.14))[0]
        regs = [(raw >> 16) & 0xFFFF, raw & 0xFFFF]
        result = adapter._registers_to_value(regs, "REAL")
        assert abs(result - 3.14) < 0.01

        # 反向转换
        back_regs = adapter._value_to_registers(3.14, "REAL")
        back_val = adapter._registers_to_value(back_regs, "REAL")
        assert abs(back_val - 3.14) < 0.01

    def test_string_conversion(self, mock_adapter):
        """测试 STRING 转换"""
        adapter = mock_adapter
        regs = adapter._value_to_registers("Hello", "STRING")
        assert len(regs) == 16  # 固定 16 个寄存器
        result = adapter._registers_to_value(regs, "STRING")
        assert result.startswith("Hello")

    def test_parse_value(self, mock_adapter):
        """测试字符串值解析"""
        adapter = mock_adapter
        assert adapter._parse_value("TRUE", "BOOL") is True
        assert adapter._parse_value("FALSE", "BOOL") is False
        assert adapter._parse_value("100", "INT") == 100
        assert adapter._parse_value("-50", "INT") == -50
        assert abs(adapter._parse_value("3.14", "REAL") - 3.14) < 0.01
        assert adapter._parse_value('"test"', "STRING") == "test"


# === VFS 集成测试 ===

class TestVFSIntegration:
    """测试与 PLCVirtualFS 的集成"""

    def test_vfs_with_inovance(self, mock_adapter):
        """测试 VFS 使用 Inovance 适配器"""
        vfs = PLCVirtualFS(mock_adapter)

        # 列出块
        blocks = vfs.ls("/devices/PLC_1/blocks")
        assert "Motor_Control.scl" in blocks
        assert "System_Status.scl" in blocks

        # 读取块
        content = vfs.cat("/devices/PLC_1/blocks/Motor_Control.scl")
        assert "Start_Button" in content
        assert "Motor_Control" in content

        # 搜索
        matches = vfs.grep("Start_Button", "/devices/PLC_1/blocks/Motor_Control.scl")
        assert len(matches) > 0

        # 查找
        paths = vfs.find("/devices/PLC_1/blocks")
        assert "/devices/PLC_1/blocks/Motor_Control.scl" in paths

    def test_vfs_write_inovance(self, mock_adapter):
        """测试通过 VFS 写入变量"""
        vfs = PLCVirtualFS(mock_adapter)

        new_code = '''// Inovance AM600/AC800 — Modbus Variable Watch
VAR_INPUT
  Start_Button : BOOL := TRUE;
  Set_Speed : INT := 2000;
END_VAR
'''
        vfs.echo(new_code, "/devices/PLC_1/blocks/Motor_Control.scl")

        read_back = vfs.cat("/devices/PLC_1/blocks/Motor_Control.scl")
        assert "Start_Button : BOOL := TRUE" in read_back
        assert "Set_Speed : INT := 2000" in read_back

    def test_vfs_diff(self, mock_adapter):
        """测试 VFS diff 功能"""
        vfs = PLCVirtualFS(mock_adapter)

        diff = vfs.diff(
            "/devices/PLC_1/blocks/Motor_Control.scl",
            "/devices/PLC_1/blocks/System_Status.scl"
        )
        assert diff is not None
        assert len(diff) > 0

    def test_vfs_repr(self, mock_adapter):
        """测试 VFS 字符串表示"""
        vfs = PLCVirtualFS(mock_adapter)
        repr_str = repr(vfs)
        assert "inovance" in repr_str


# === InovanceAM600Adapter 单元测试（模拟 Modbus）===

class TestInovanceAM600Adapter:
    """测试 InovanceAM600Adapter（使用模拟的 Modbus 客户端）"""

    @patch('plc_vfs.adapters.inovance.ModbusTcpClient')
    def test_connect_success(self, mock_client_class, block_map_file):
        """测试成功连接"""
        mock_client = MagicMock()
        mock_client.connect.return_value = True
        mock_client_class.return_value = mock_client

        adapter = InovanceAM600Adapter(
            host="192.168.1.10",
            port=502,
            block_map_path=block_map_file
        )
        adapter.connect()
        assert adapter.is_connected()
        mock_client_class.assert_called_once()

    @patch('plc_vfs.adapters.inovance.ModbusTcpClient')
    def test_connect_failure(self, mock_client_class, block_map_file):
        """测试连接失败"""
        mock_client = MagicMock()
        mock_client.connect.return_value = False
        mock_client_class.return_value = mock_client

        adapter = InovanceAM600Adapter(
            host="192.168.1.10",
            block_map_path=block_map_file
        )
        with pytest.raises(Exception):
            adapter.connect()

    @patch('plc_vfs.adapters.inovance.ModbusTcpClient')
    def test_read_coils(self, mock_client_class, block_map_file):
        """测试读取线圈"""
        mock_result = MagicMock()
        mock_result.isError.return_value = False
        mock_result.bits = [True, False]

        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.read_coils.return_value = mock_result
        mock_client_class.return_value = mock_client

        adapter = InovanceAM600Adapter(
            host="192.168.1.10",
            block_map_path=block_map_file
        )
        adapter._client = mock_client
        adapter._mock_connected = True  # 标记为已连接

        # 模拟读取变量
        variables = [
            {"name": "TestBool", "type": "BOOL", "modbus": {"function": 1, "address": 0}}
        ]
        values = adapter._read_variables(variables)
        assert values["TestBool"] is True

    @patch('plc_vfs.adapters.inovance.ModbusTcpClient')
    def test_write_holding_registers(self, mock_client_class, block_map_file):
        """测试写入保持寄存器"""
        mock_result = MagicMock()
        mock_result.isError.return_value = False

        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.write_register.return_value = mock_result
        mock_client_class.return_value = mock_client

        adapter = InovanceAM600Adapter(
            host="192.168.1.10",
            block_map_path=block_map_file
        )
        adapter._client = mock_client
        adapter._mock_connected = True

        variables = [
            {"name": "TestInt", "type": "INT", "modbus": {"function": 3, "address": 0}}
        ]
        values = {"TestInt": 100}
        result = adapter._write_variables(variables, values)
        assert result is True

    def test_import_error(self, block_map_file):
        """测试 pymodbus 未安装时的错误"""
        with patch('plc_vfs.adapters.inovance.ModbusTcpClient', None):
            adapter = InovanceAM600Adapter(
                host="192.168.1.10",
                block_map_path=block_map_file
            )
            with pytest.raises(ImportError):
                adapter.connect()


# === 配置管理测试 ===

class TestConfigManagement:
    """测试配置加载和保存"""

    def test_load_block_map(self, block_map_file):
        """测试加载配置文件"""
        adapter = MockInovanceAdapter(block_map_path=block_map_file)
        blocks = adapter.list_blocks()
        assert "Motor_Control" in blocks
        assert "System_Status" in blocks

    def test_reload_block_map(self, block_map_file, sample_block_map):
        """测试重新加载配置"""
        adapter = MockInovanceAdapter(block_map_path=block_map_file)
        adapter.connect()

        # 添加新块
        adapter.add_block_definition("New_Block", {
            "type": "FB",
            "variables": []
        })
        assert "New_Block" in adapter.list_blocks()

        # 重新加载（会丢失动态添加的块）
        adapter.reload_block_map()
        assert "New_Block" not in adapter.list_blocks()

    def test_save_block_map(self, block_map_file):
        """测试保存配置"""
        adapter = MockInovanceAdapter(block_map_path=block_map_file)
        adapter.connect()

        fd, new_path = tempfile.mkstemp(suffix='.json')
        os.close(fd)

        try:
            adapter.save_block_map(new_path)
            with open(new_path, 'r') as f:
                saved = json.load(f)
            assert "Motor_Control" in saved["blocks"]
        finally:
            os.unlink(new_path)

    def test_add_block_definition(self, block_map_file):
        """测试动态添加块定义"""
        adapter = MockInovanceAdapter(block_map_path=block_map_file)
        adapter.add_block_definition("TestBlock", {
            "type": "FC",
            "variables": [
                {"name": "TestVar", "type": "BOOL", "modbus": {"function": 1, "address": 100}}
            ]
        })
        assert "TestBlock" in adapter.list_blocks()


# === 运行入口 ===

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
