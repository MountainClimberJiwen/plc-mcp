"""
PLC Virtual Filesystem (PLC-VFS)

让 AI 用 cat、diff、grep 操作任何品牌的 PLC 项目。
无需网络，无需 FUSE，纯 Python 虚拟文件系统。
"""

from .core import PLCVirtualFS, PLCBlock
from .adapters.base import PLCAdapter

__version__ = "0.1.0"
__all__ = ["PLCVirtualFS", "PLCBlock", "PLCAdapter"]
