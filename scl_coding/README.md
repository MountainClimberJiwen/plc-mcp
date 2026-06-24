# TIA Portal CPU Creator

This program uses the TIA Portal Openness API to create a Siemens S7-1513 CPU in an existing TIA Portal project.

## Prerequisites

1. TIA Portal V19 or higher installed
2. TIA Portal Openness feature enabled
3. .NET 7.0 Runtime installed

## Configuration

1. Edit the `config.txt` file with your TIA Portal installation paths:
```
# TIA Portal 安装路径
TiaPortalPath=E:\Program Files\Siemens\Automation\Portal V19

# Project path to .ap Files
ProjectPath=E:\TIA_Projects\test3\SimpleCounter2\SimpleCounter2.ap19

# Siemens.Engineering.dll 路径
EngineeringDllPath=E:\Program Files\Siemens\Automation\Portal V19\Bin\PublicAPI\Siemens.Engineering.dll
```

## Usage

1. Make sure TIA Portal is running and your project is open
2. Run the program
3. The program will:
   - Connect to TIA Portal
   - Create a new S7-1513 CPU named "PLC_1"
   - Configure basic network settings (IP: 192.168.0.1)

## Notes

- If a device named "PLC_1" already exists, the program will skip creation
- The program will automatically configure the PROFINET interface with a default IP address
- Make sure you have appropriate permissions to modify the TIA Portal project 