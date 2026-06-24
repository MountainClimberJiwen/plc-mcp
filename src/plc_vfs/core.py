"""
PLC Virtual Filesystem (PLC-VFS)
最小可行实现：将 TIA Portal 项目映射为本地虚拟文件系统

无需网络，无需 FUSE，纯 Python 实现
可直接集成到现有 plc-mcp 的 MCP Server 中
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import json
import difflib
import os


@dataclass
class PLCBlock:
    """PLC 程序块数据对象"""
    name: str
    block_type: str = "FC"  # OB, FB, FC, DB, UDT
    language: str = "SCL"   # SCL, STL, LAD, FBD
    source_code: Optional[str] = None
    xml_representation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def extension(self) -> str:
        return ".scl" if self.language == "SCL" else ".xml"
    
    def to_file_content(self, format: str = "scl") -> str:
        if format == "scl":
            return self.source_code or ""
        return self.xml_representation or ""


class PLCAdapter(ABC):
    """PLC 品牌适配器基类"""
    
    @property
    @abstractmethod
    def brand(self) -> str:
        pass
    
    @abstractmethod
    def read_block(self, block_name: str) -> PLCBlock:
        """读取程序块"""
        pass
    
    @abstractmethod
    def write_block(self, block: PLCBlock) -> bool:
        """写入程序块"""
        pass
    
    @abstractmethod
    def list_blocks(self) -> List[str]:
        """列出所有程序块名称"""
        pass
    
    @abstractmethod
    def compile(self) -> Dict[str, Any]:
        """编译项目"""
        pass
    
    def block_exists(self, block_name: str) -> bool:
        return block_name in self.list_blocks()


class SiemensTIAAdapter(PLCAdapter):
    """
    Siemens TIA Portal 适配器
    使用 pythonnet 调用 TIA Openness API
    """
    
    def __init__(self, project_path: str, tia_host: str = "localhost"):
        self.project_path = project_path
        self.tia_host = tia_host
        self._tia_portal = None
        self._project = None
        self._plc_software = None
    
    @property
    def brand(self) -> str:
        return "siemens"
    
    def connect(self):
        """连接到 TIA Portal"""
        import clr
        import System
        
        # 加载 Siemens.Engineering.dll
        clr.AddReference("Siemens.Engineering")
        from Siemens.Engineering import TiaPortal, TiaPortalMode
        
        # 连接或启动 TIA Portal
        processes = TiaPortal.GetProcesses()
        if processes:
            self._tia_portal = processes[0].Attach()
        else:
            self._tia_portal = TiaPortal(TiaPortalMode.WithUserInterface)
        
        # 打开项目
        self._project = self._tia_portal.Projects.Open(
            System.IO.FileInfo(self.project_path)
        )
        
        # 获取第一个 PLC 的软件对象
        self._plc_software = self._get_plc_software()
    
    def _get_plc_software(self):
        """获取 PLC 软件容器"""
        from Siemens.Engineering.HW.Features import SoftwareContainer
        
        for device in self._project.Devices:
            for item in device.DeviceItems:
                try:
                    container = item.GetService[SoftwareContainer]()
                    if container and container.Software:
                        from Siemens.Engineering.SW import PlcSoftware
                        if isinstance(container.Software, PlcSoftware):
                            return container.Software
                except:
                    continue
        return None
    
    def read_block(self, block_name: str) -> PLCBlock:
        """从 TIA Portal 读取程序块"""
        from Siemens.Engineering.SW.Blocks import PlcBlock
        
        block = self._plc_software.BlockGroup.Blocks.Find(block_name)
        if not block:
            raise FileNotFoundError(f"Block {block_name} not found in TIA Portal")
        
        # 导出为临时 XML 获取源码
        import System.IO
        temp_path = System.IO.Path.GetTempFileName() + ".xml"
        block.Export(System.IO.FileInfo(temp_path))
        
        with open(temp_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # 提取 SCL 源码（简化实现）
        source_code = self._extract_scl_from_xml(xml_content)
        
        return PLCBlock(
            name=block.Name,
            block_type=str(block.BlockType),
            language=str(block.ProgrammingLanguage),
            source_code=source_code,
            xml_representation=xml_content
        )
    
    def write_block(self, block: PLCBlock) -> bool:
        """将程序块写入 TIA Portal"""
        from Siemens.Engineering.SW.ExternalSources import ExternalSource
        
        # 创建临时 SCL 文件
        temp_path = f"C:/Temp/{block.name}_{os.urandom(4).hex()}.scl"
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(block.source_code)
        
        # 通过 ExternalSource 导入
        import System.IO
        external_source = self._plc_software.ExternalSourceGroup.ExternalSources.CreateFromFile(
            block.name + "_import",
            System.IO.FileInfo(temp_path)
        )
        external_source.GenerateBlocksFromSource()
        
        # 清理临时文件
        os.remove(temp_path)
        
        return True
    
    def list_blocks(self) -> List[str]:
        """列出所有程序块"""
        return [block.Name for block in self._plc_software.BlockGroup.Blocks]
    
    def compile(self) -> Dict[str, Any]:
        """编译项目"""
        from Siemens.Engineering.Compiler import Compiler
        
        compiler = self._plc_software.GetService[Compiler]()
        result = compiler.Compile()
        
        return {
            'success': str(result.State) == 'Success',
            'warnings': len(result.Messages.Warnings),
            'errors': len(result.Messages.Errors)
        }
    
    def _extract_scl_from_xml(self, xml: str) -> str:
        """从 TIA Openness XML 提取 SCL 源码"""
        # 简化实现：实际应使用 XML 解析
        import re
        match = re.search(r'<ProgrammingLanguage>SCL</ProgrammingLanguage>.*?<Text>(.*?)</Text>', xml, re.DOTALL)
        if match:
            return match.group(1)
        return "// SCL source not found in XML"


class MockTIAAdapter(PLCAdapter):
    """
    Mock TIA 适配器（用于测试，无需真实 TIA Portal）
    """
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self._blocks: Dict[str, PLCBlock] = {
            "Block_1": PLCBlock(
                name="Block_1",
                block_type="FC",
                language="SCL",
                source_code='''FUNCTION "Block_1" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
    // Motor control logic
    #Motor_On := #Start_Button AND NOT #Stop_Button;
    IF #Motor_On THEN
        #Motor_Speed := #Set_Speed;
    ELSE
        #Motor_Speed := 0;
    END_IF;
END_FUNCTION
'''
            ),
            "Block_4": PLCBlock(
                name="Block_4",
                block_type="FB",
                language="SCL",
                source_code='''FUNCTION_BLOCK "Block_4"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
   VAR_INPUT 
      Input_1 : Int;
      Input_2 : Int;
   END_VAR

   VAR_OUTPUT 
      Output_1 : Int;
   END_VAR

BEGIN
    Output_1 := Input_1 + Input_2;
END_FUNCTION_BLOCK
'''
            )
        }
    
    @property
    def brand(self) -> str:
        return "siemens"
    
    def read_block(self, block_name: str) -> PLCBlock:
        if block_name not in self._blocks:
            raise FileNotFoundError(f"Block {block_name} not found")
        return self._blocks[block_name]
    
    def write_block(self, block: PLCBlock) -> bool:
        self._blocks[block.name] = block
        return True
    
    def list_blocks(self) -> List[str]:
        return list(self._blocks.keys())
    
    def compile(self) -> Dict[str, Any]:
        return {'success': True, 'warnings': 0, 'errors': 0}


class PLCVirtualFS:
    """
    PLC 虚拟文件系统
    将 PLC 项目映射为类 pathlib 的 API
    
    使用示例:
        vfs = PLCVirtualFS(MockTIAAdapter("test.ap19"))
        
        # 读取块
        print(vfs.cat("/devices/PLC_1/blocks/Block_1.scl"))
        
        # 写入块
        vfs.echo("new code", "/devices/PLC_1/blocks/Block_1.scl")
        
        # 列出目录
        print(vfs.ls("/devices/PLC_1/blocks"))
        
        # 比较差异
        print(vfs.diff("/devices/PLC_1/blocks/Block_1.scl", "/backup/Block_1.scl"))
    """
    
    def __init__(self, adapter: PLCAdapter):
        self.adapter = adapter
        self._cache: Dict[str, str] = {}  # 路径 -> 内容缓存
        self._mounts: Dict[str, str] = {}  # 虚拟路径 -> 真实路径
    
    # === 核心文件操作 ===
    
    def cat(self, path: str) -> str:
        """读取文件内容 (类似 shell cat)"""
        # 检查缓存
        if path in self._cache:
            return self._cache[path]
        
        # 解析路径
        block_name = self._parse_block_path(path)
        if block_name:
            block = self.adapter.read_block(block_name)
            content = block.to_file_content("scl" if path.endswith(".scl") else "xml")
            self._cache[path] = content
            return content
        
        # 检查挂载点
        for vpath, real in self._mounts.items():
            if path.startswith(vpath):
                real_path = path.replace(vpath, real)
                with open(real_path, 'r') as f:
                    return f.read()
        
        raise FileNotFoundError(f"{path} not found")
    
    def echo(self, content: str, path: str):
        """写入文件内容 (类似 shell echo > file)"""
        self._cache[path] = content
        
        # 如果是 PLC 块路径，写回 IDE
        block_name = self._parse_block_path(path)
        if block_name:
            block = PLCBlock(
                name=block_name,
                source_code=content,
                language="SCL"
            )
            self.adapter.write_block(block)
        
        # 如果是挂载点，写回真实文件
        for vpath, real in self._mounts.items():
            if path.startswith(vpath):
                real_path = path.replace(vpath, real)
                os.makedirs(os.path.dirname(real_path), exist_ok=True)
                with open(real_path, 'w') as f:
                    f.write(content)
    
    def ls(self, path: str = "/") -> List[str]:
        """列出目录内容 (类似 shell ls)"""
        parts = path.strip('/').split('/')
        
        if path == '/' or path == '':
            return ['devices', 'networks', 'project.json']
        
        if parts[0] == 'devices':
            if len(parts) == 1:
                return ['PLC_1']  # 可扩展为动态获取
            if len(parts) == 2 and parts[1] == 'PLC_1':
                return ['blocks', 'tags', 'types']
            if len(parts) == 3 and parts[2] == 'blocks':
                return [f"{name}.scl" for name in self.adapter.list_blocks()]
        
        return []
    
    def diff(self, path_a: str, path_b: str) -> str:
        """比较两个文件差异 (类似 shell diff)"""
        a = self.cat(path_a)
        b = self.cat(path_b)
        
        return '\n'.join(difflib.unified_diff(
            a.splitlines(), b.splitlines(),
            fromfile=path_a, tofile=path_b
        ))
    
    def cp(self, src: str, dst: str):
        """复制文件 (类似 shell cp)"""
        content = self.cat(src)
        self.echo(content, dst)
    
    def grep(self, pattern: str, path: str) -> List[str]:
        """搜索文件内容 (类似 shell grep)"""
        content = self.cat(path)
        lines = content.splitlines()
        return [line for line in lines if pattern in line]
    
    def find(self, path: str, pattern: str = "*.scl") -> List[str]:
        """查找文件 (类似 shell find)"""
        if path == '/devices/PLC_1/blocks':
            return [f"/devices/PLC_1/blocks/{name}.scl" 
                    for name in self.adapter.list_blocks()]
        return []
    
    # === 挂载点管理 ===
    
    def mount(self, virtual_path: str, real_path: str):
        """挂载真实目录到虚拟路径"""
        self._mounts[virtual_path] = real_path
    
    def umount(self, virtual_path: str):
        """卸载"""
        if virtual_path in self._mounts:
            del self._mounts[virtual_path]
    
    # === 缓存管理 ===
    
    def flush(self):
        """刷新所有缓存到 IDE"""
        for path, content in self._cache.items():
            block_name = self._parse_block_path(path)
            if block_name:
                block = PLCBlock(name=block_name, source_code=content)
                self.adapter.write_block(block)
        self._cache.clear()
    
    def invalidate(self, path: str):
        """使缓存失效"""
        if path in self._cache:
            del self._cache[path]
    
    # === 辅助方法 ===
    
    def _parse_block_path(self, path: str) -> Optional[str]:
        """解析路径是否为 PLC 块路径"""
        parts = path.strip('/').split('/')
        if (len(parts) >= 4 and 
            parts[0] == 'devices' and 
            parts[2] == 'blocks'):
            return parts[3].replace('.scl', '').replace('.xml', '')
        return None
    
    def __repr__(self):
        return f"PLCVirtualFS(brand={self.adapter.brand}, blocks={len(self.adapter.list_blocks())})"


# === MCP Server 集成 ===

class PLCVFSMCPServer:
    """
    集成 PLC-VFS 的 MCP Server
    提供统一的 MCP Tools 给 AI 调用
    """
    
    def __init__(self, vfs: PLCVirtualFS):
        self.vfs = vfs
    
    def get_tools(self) -> List[Dict]:
        """返回 MCP Tools 定义"""
        return [
            {
                "name": "plc_read_block",
                "description": "读取 PLC 程序块源码",
                "parameters": {
                    "block_name": "程序块名称，如 Block_1",
                    "format": "scl 或 xml"
                }
            },
            {
                "name": "plc_write_block",
                "description": "写入 PLC 程序块源码",
                "parameters": {
                    "block_name": "程序块名称",
                    "code": "SCL 源码"
                }
            },
            {
                "name": "plc_list_blocks",
                "description": "列出所有程序块"
            },
            {
                "name": "plc_diff",
                "description": "比较两个程序块差异"
            },
            {
                "name": "plc_compile",
                "description": "编译项目"
            }
        ]
    
    def read_block(self, block_name: str, format: str = "scl") -> str:
        """MCP Tool: 读取程序块"""
        path = f"/devices/PLC_1/blocks/{block_name}.{format}"
        return self.vfs.cat(path)
    
    def write_block(self, block_name: str, code: str) -> str:
        """MCP Tool: 写入程序块"""
        path = f"/devices/PLC_1/blocks/{block_name}.scl"
        self.vfs.echo(code, path)
        
        # 编译验证
        result = self.vfs.adapter.compile()
        if result['success']:
            return f"Block {block_name} written and compiled successfully"
        else:
            return f"Block {block_name} written but compile failed: {result}"
    
    def list_blocks(self) -> List[str]:
        """MCP Tool: 列出程序块"""
        return self.vfs.ls("/devices/PLC_1/blocks")
    
    def diff_blocks(self, block_a: str, block_b: str) -> str:
        """MCP Tool: 比较程序块"""
        path_a = f"/devices/PLC_1/blocks/{block_a}.scl"
        path_b = f"/devices/PLC_1/blocks/{block_b}.scl"
        return self.vfs.diff(path_a, path_b)
    
    def compile(self) -> Dict:
        """MCP Tool: 编译"""
        return self.vfs.adapter.compile()


# === 测试 ===

if __name__ == "__main__":
    # 使用 Mock 适配器测试（无需真实 TIA Portal）
    adapter = MockTIAAdapter("test.ap19")
    vfs = PLCVirtualFS(adapter)
    
    print("=== PLC Virtual Filesystem Demo ===")
    print(f"VFS: {vfs}")
    print()
    
    # 1. 列出块
    print("1. 列出所有程序块:")
    blocks = vfs.ls("/devices/PLC_1/blocks")
    print(f"   {blocks}")
    print()
    
    # 2. 读取块
    print("2. 读取 Block_1:")
    content = vfs.cat("/devices/PLC_1/blocks/Block_1.scl")
    print(f"   {content[:200]}...")
    print()
    
    # 3. 修改块
    print("3. 修改 Block_1:")
    new_code = '''FUNCTION "Block_1" : Void
BEGIN
    // Updated motor control
    #Motor_On := #Start_Button AND #Safety_OK AND NOT #Emergency_Stop;
    IF #Motor_On THEN
        #Motor_Speed := #Set_Speed * 0.9;  // 90% max speed
    ELSE
        #Motor_Speed := 0;
    END_IF;
END_FUNCTION
'''
    vfs.echo(new_code, "/devices/PLC_1/blocks/Block_1.scl")
    print("   Written new code")
    print()
    
    # 4. 比较差异
    print("4. 比较 Block_1 和 Block_4:")
    diff = vfs.diff("/devices/PLC_1/blocks/Block_1.scl", "/devices/PLC_1/blocks/Block_4.scl")
    print(f"   {diff[:500]}...")
    print()
    
    # 5. 搜索
    print("5. 搜索包含 'Motor' 的行:")
    matches = vfs.grep("Motor", "/devices/PLC_1/blocks/Block_1.scl")
    for line in matches:
        print(f"   {line}")
    print()
    
    # 6. 挂载本地目录
    print("6. 挂载本地目录并导出:")
    vfs.mount("/workspace", "/tmp/plc_workspace")
    vfs.cp("/devices/PLC_1/blocks/Block_1.scl", "/workspace/Block_1_backup.scl")
    print(f"   Exported to /workspace/Block_1_backup.scl")
    print()
    
    # 7. MCP Server 集成
    print("7. MCP Server 工具调用:")
    mcp = PLCVFSMCPServer(vfs)
    print(f"   Available tools: {[t['name'] for t in mcp.get_tools()]}")
    print(f"   Compile result: {mcp.compile()}")
    
    print("\n=== Demo Complete ===")
    print("\n这个 VFS 可以:")
    print("- 让 AI 用 cat/ls/diff/grep 操作 PLC 项目")
    print("- 缓存读写减少 IDE 交互次数")
    print("- 挂载本地目录实现导入/导出")
    print("- 集成到 MCP Server 提供统一 Tools")
