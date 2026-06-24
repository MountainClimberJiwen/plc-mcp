from . import server
import asyncio
import argparse

def main():
    """Main entry point for the package."""
    parser = argparse.ArgumentParser(description='PLC MCP Server')
    parser.add_argument('--project-path', 
                       default="./TIA_Projects/test3",
                       help='Path to TIA project file')
    parser.add_argument('--project-name', 
                       default="SimpleCounter2",
                       help='Name of TIA project')
    
    args = parser.parse_args()
    asyncio.run(server.main(args.project_path, args.project_name))


# Optionally expose other important items at package level
__all__ = ["main", "server"]
