@echo off
echo 准备发布文件...

REM 设置目录
set PUBLISH_DIR=publish
set LIB_DIR=%PUBLISH_DIR%\lib

REM 创建发布目录
if exist %PUBLISH_DIR% rd /s /q %PUBLISH_DIR%
mkdir %PUBLISH_DIR%
mkdir %LIB_DIR%

REM 发布程序
dotnet publish -c Release -o %PUBLISH_DIR%

REM 复制配置文件模板
echo # TIA Portal 安装路径 > %PUBLISH_DIR%\config.txt
echo TiaPortalPath=C:\Program Files\Siemens\Automation\Portal V19 >> %PUBLISH_DIR%\config.txt
echo. >> %PUBLISH_DIR%\config.txt
echo # Siemens.Engineering.dll 路径 >> %PUBLISH_DIR%\config.txt
echo EngineeringDllPath=C:\Program Files\Siemens\Automation\Portal V19\Bin\PublicAPI\Siemens.Engineering.dll >> %PUBLISH_DIR%\config.txt

REM 创建说明文件
echo TIA Openness 应用程序使用说明 > %PUBLISH_DIR%\README.txt
echo ========================== >> %PUBLISH_DIR%\README.txt
echo. >> %PUBLISH_DIR%\README.txt
echo 1. 安装要求： >> %PUBLISH_DIR%\README.txt
echo    - 安装 TIA Portal V19 或更高版本 >> %PUBLISH_DIR%\README.txt
echo    - 确保已启用 Openness 功能 >> %PUBLISH_DIR%\README.txt
echo. >> %PUBLISH_DIR%\README.txt
echo 2. 配置步骤： >> %PUBLISH_DIR%\README.txt
echo    - 编辑 config.txt 文件 >> %PUBLISH_DIR%\README.txt
echo    - 设置正确的 TIA Portal 安装路径 >> %PUBLISH_DIR%\README.txt
echo. >> %PUBLISH_DIR%\README.txt
echo 3. 运行程序： >> %PUBLISH_DIR%\README.txt
echo    - 直接运行 MyFirstApp.exe >> %PUBLISH_DIR%\README.txt
echo    - 或通过命令行：MyFirstApp.exe [PLC名称] [SCL文件路径] >> %PUBLISH_DIR%\README.txt
echo. >> %PUBLISH_DIR%\README.txt
echo 4. 文件说明： >> %PUBLISH_DIR%\README.txt
echo    - MyFirstApp.exe：主程序 >> %PUBLISH_DIR%\README.txt
echo    - config.txt：配置文件 >> %PUBLISH_DIR%\README.txt
echo    - lib\：依赖库目录 >> %PUBLISH_DIR%\README.txt
echo. >> %PUBLISH_DIR%\README.txt
echo 5. 注意事项： >> %PUBLISH_DIR%\README.txt
echo    - 确保有足够的权限访问 TIA Portal >> %PUBLISH_DIR%\README.txt
echo    - 保持所有文件在同一目录下 >> %PUBLISH_DIR%\README.txt

echo 发布完成！文件位于 %PUBLISH_DIR% 目录 