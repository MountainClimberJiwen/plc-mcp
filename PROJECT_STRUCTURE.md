plc-universal-mcp/
├── README.md                          # 项目总览
├── docs/
│   ├── architecture.md                # 架构设计文档
│   ├── siemens-tia-guide.md          # TIA Portal 集成指南
│   ├── beckhoff-guide.md             # TwinCAT 集成指南
│   └── api-reference.md              # API 参考
├── src/
│   ├── plc_vfs/                       # 虚拟文件系统核心
│   │   ├── __init__.py
│   │   ├── core.py                    # VFS 核心实现
│   │   ├── adapters/                  # 品牌适配器
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # 适配器基类
│   │   │   ├── siemens.py             # TIA Portal 适配器
│   │   │   ├── beckhoff.py            # TwinCAT 适配器
│   │   │   └── mock.py                # Mock 适配器（测试）
│   │   ├── transpiler/                # 代码转换器
│   │   │   ├── __init__.py
│   │   │   ├── siemens_to_iec.py
│   │   │   └── iec_to_beckhoff.py
│   │   └── mounts/                    # 挂载点管理
│   │       ├── __init__.py
│   │       ├── local.py               # 本地磁盘挂载
│   │       ├── git.py                 # Git 仓库挂载
│   │       └── s3.py                  # S3 挂载
│   ├── mcp_server/                    # MCP 服务器
│   │   ├── __init__.py
│   │   ├── server.py                  # 主服务器
│   │   ├── tools.py                   # MCP Tools 定义
│   │   └── prompts.py                 # 系统提示词
│   ├── web_server/                    # Web 服务端（HTTP API）
│   │   ├── __init__.py
│   │   ├── app.py
│   │   └── routes/
│   └── extensions/                    # IDE 扩展
│       └── vscode/                    # VS Code 扩展
│           ├── package.json
│           └── src/
├── tests/
│   ├── test_vfs.py
│   ├── test_adapters.py
│   └── fixtures/
│       └── test_project.ap19
├── examples/
│   ├── siemens_demo.py
│   ├── beckhoff_demo.py
│   └── cross_brand_migration.py
├── scripts/
│   ├── setup_tia_openness.ps1         # Windows 环境初始化
│   └── install.sh                     # 跨平台安装
├── config/
│   ├── siemens_config.yaml
│   └── beckhoff_config.yaml
├── pyproject.toml
└── .github/
    └── workflows/
        └── test.yml
