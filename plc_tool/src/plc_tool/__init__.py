import os
from . import server
import asyncio
import argparse

def main():
    """Main entry point for the package."""
    parser = argparse.ArgumentParser(description='PLC MCP Server')
    parser.add_argument('--project-path',
                       default="./TIA_Projects/test3",
                       help='Path to TIA project file or Inovance block map JSON')
    parser.add_argument('--project-name',
                       default="SimpleCounter2",
                       help='Name of TIA project')
    parser.add_argument('--brand',
                       default="siemens",
                       choices=['siemens', 'inovance', 'mock'],
                       help='PLC brand: siemens, inovance, or mock')
    parser.add_argument('--host',
                       default=None,
                       help='Inovance PLC host IP (default: 192.168.1.10 or env INOVANCE_PLC_HOST)')
    parser.add_argument('--port',
                       type=int,
                       default=502,
                       help='Inovance Modbus TCP port (default: 502)')
    parser.add_argument('--use-vfs', action='store_true',
                       help='Enable PLC Virtual Filesystem integration')

    args = parser.parse_args()
    use_vfs = args.use_vfs or os.environ.get('PLC_MCP_USE_VFS', '0') == '1'
    asyncio.run(server.main(
        args.project_path,
        args.project_name,
        use_vfs=use_vfs,
        brand=args.brand,
        host=args.host,
        port=args.port,
    ))


# Optionally expose other important items at package level
__all__ = ["main", "server"]
