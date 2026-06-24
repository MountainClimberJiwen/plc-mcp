@echo off
setlocal

REM 从config.txt读取DLL路径
for /f "tokens=1,2 delims==" %%a in ('type config.txt ^| findstr /v "#"') do (
    if "%%a"=="EngineeringDllPath" (
        set "DLL_PATH=%%b"
    )
)

REM 设置环境变量
set PATH=%DLL_PATH:\PublicAPI\Siemens.Engineering.dll=%\PublicAPI;%PATH%

REM 运行程序
bin\Debug\net48\MyFirstApp.exe %* 