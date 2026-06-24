using System;
using System.IO;
using Serilog;
using System.Reflection;
using System.Linq;

namespace Web.Config
{
    public class AppConfig
    {
        public string TiaPortalPath { get; set; }
        public string EngineeringDllPath { get; set; }
        public string ProjectPath { get; set; }

        public string SclCodeRootDir { get; set; }

        private static readonly string ConfigFilePath = "config.txt";

        public static AppConfig Load()
        {
            if (!File.Exists(ConfigFilePath))
            {
                Log.Information("配置文件不存在，请先创建config.txt文件，格式如下：");
                Log.Information("TiaPortalPath=C:\\Program Files\\Siemens\\Automation\\Portal V19");
                Log.Information("ProjectPath=E:\\tia\\test\\test.ap19");
                return null;
            }

            try
            {
                var config = new AppConfig();
                var lines = File.ReadAllLines(ConfigFilePath);
                foreach (var line in lines)
                {
                    Console.WriteLine($"line: {line}");
                    if (line.Trim().StartsWith("#")) continue;
                    
                    var parts = line.Split(new[] { '=' }, 2);
                    if (parts.Length != 2) continue;
                    
                    var key = parts[0].Trim();
                    var value = parts[1].Trim();
                    
                    switch (key)
                    {
                        case "TiaPortalPath":
                            config.TiaPortalPath = value;
                            break;
                        case "ProjectPath":
                            config.ProjectPath = value;
                            break;
                         case "SclCodeRootDir":
                             config.SclCodeRootDir = value;
                             break;
                        case "EngineeringDllPath":
                            // 保留兼容性，但不再使用
                            Console.WriteLine("警告：EngineeringDllPath配置已废弃，将自动检测DLL路径");
                            break;
                    }
                }

                // 自动检测EngineeringDllPath
                config.EngineeringDllPath = FindEngineeringDll(config.TiaPortalPath);
                if (string.IsNullOrEmpty(config.EngineeringDllPath))
                {
                    Console.WriteLine("错误：无法找到Siemens.Engineering.dll，请检查TIA Portal是否正确安装或DLL是否在发布目录中");
                    return null;
                }

                // 验证路径
                if (!Directory.Exists(config.TiaPortalPath))
                {
                    Console.WriteLine($"错误：TIA Portal路径不存在: {config.TiaPortalPath}");
                    return null;
                }

                if (!File.Exists(config.ProjectPath))
                {
                    Console.WriteLine($"错误：Project文件不存在: {config.ProjectPath}");
                    throw new InvalidOperationException($"Project file ({config.ProjectPath}) does not exist");
                }

                // 加载DLL
                try
                {
                    Assembly.LoadFile(config.EngineeringDllPath);
                    Console.WriteLine($"成功加载 Siemens.Engineering.dll: {config.EngineeringDllPath}");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"加载DLL失败: {ex.Message}");
                    return null;
                }

                return config;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"读取配置文件出错: {ex.Message}");
                return null;
            }
        }

        private static string FindEngineeringDll(string tiaPortalPath)
        {
            // 首先检查发布目录中是否有Siemens.Engineering.dll
            var publishDirPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Siemens.Engineering.dll");
            if (File.Exists(publishDirPath))
            {
                Console.WriteLine($"使用发布目录中的Siemens.Engineering.dll: {publishDirPath}");
                return publishDirPath;
            }

            // 常见的Siemens.Engineering.dll路径
            var possiblePaths = new[]
            {
                Path.Combine(tiaPortalPath, "Bin", "PublicAPI", "Siemens.Engineering.dll"),
                Path.Combine(tiaPortalPath, "PublicAPI", "V19", "Siemens.Engineering.dll"),
                Path.Combine(tiaPortalPath, "PublicAPI", "V18", "Siemens.Engineering.dll"),
                Path.Combine(tiaPortalPath, "PublicAPI", "V17", "Siemens.Engineering.dll"),
                Path.Combine(tiaPortalPath, "PublicAPI", "V16", "Siemens.Engineering.dll"),
                Path.Combine(tiaPortalPath, "PublicAPI", "V15", "Siemens.Engineering.dll")
            };

            foreach (var path in possiblePaths)
            {
                if (File.Exists(path))
                {
                    Console.WriteLine($"找到Siemens.Engineering.dll: {path}");
                    return path;
                }
            }

            // 如果没找到，尝试搜索整个TIA Portal目录
            try
            {
                var engineeringDll = Directory.GetFiles(tiaPortalPath, "Siemens.Engineering.dll", SearchOption.AllDirectories)
                    .FirstOrDefault();
                
                if (!string.IsNullOrEmpty(engineeringDll))
                {
                    Console.WriteLine($"通过搜索找到Siemens.Engineering.dll: {engineeringDll}");
                    return engineeringDll;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"搜索Siemens.Engineering.dll时出错: {ex.Message}");
            }

            return null;
        }
    }
} 