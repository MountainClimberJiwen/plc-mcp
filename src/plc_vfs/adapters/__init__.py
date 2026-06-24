"""
PLC 品牌适配器基类
定义所有 PLC 品牌必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from ..core import PLCBlock


class PLCAdapter(ABC):
    """PLC 品牌适配器基类"""
    
    @property
    @abstractmethod
    def brand(self) -> str:
        """品牌标识，如 'siemens', 'beckhoff'"""
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
        """检查程序块是否存在"""
        return block_name in self.list_blocks()
    
    def connect(self):
        """连接到 IDE（可选）"""
        pass
    
    def disconnect(self):
        """断开 IDE 连接（可选）"""
        pass
