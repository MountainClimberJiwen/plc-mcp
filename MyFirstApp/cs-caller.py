import subprocess

# 指定 C# 可执行文件路径
# E:\pycharm-projects\tia-openness\c-sharp\MyFirstApp\bin\Debug\net8.0\MyFirstApp.exe
exe_path = r"E:\\pycharm-projects\\tia-openness\\c-sharp\\MyFirstApp\\bin\\Debug\\net8.0\\MyFirstApp.exe"

# 执行 C# 程序
result = subprocess.run([exe_path], capture_output=True, text=True)

# 打印输出
print("标准输出 stdout:")
print(result.stdout)

print("标准错误 stderr:")
print(result.stderr)

print("返回码 return code:")
print(result.returncode)