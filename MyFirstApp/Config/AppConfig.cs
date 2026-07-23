using System;
using System.IO;
using System.Reflection;

namespace MyFirstApp.Config
{
    public class AppConfig
    {
        public string TiaPortalPath { get; set; }
        public string EngineeringDllPath { get; set; }
        public string ProjectPath { get; set; }

        private static readonly string ConfigFilePath = "config.txt";

        public static AppConfig Load()
        {
            if (!File.Exists(ConfigFilePath))
            {
                Console.WriteLine("配置文件不存在，请先创建config.txt文件，格式如下：");
                Console.WriteLine("TiaPortalPath=C:\\Program Files\\Siemens\\Automation\\Portal V19");
                Console.WriteLine("EngineeringDllPath=C:\\Program Files\\Siemens\\Automation\\Portal V19\\Bin\\PublicAPI\\Siemens.Engineering.dll");
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
                        case "EngineeringDllPath":
                            config.EngineeringDllPath = value;
                            break;
                        case "ProjectPath":
                            config.ProjectPath = value;
                            break;
                    }
                }

                // 验证路径
                if (!Directory.Exists(config.TiaPortalPath))
                {
                    Console.WriteLine($"错误：TIA Portal路径不存在: {config.TiaPortalPath}");
                    return null;
                }
                if (!File.Exists(config.EngineeringDllPath))
                {
                    Console.WriteLine($"错误：Engineering DLL文件不存在: {config.EngineeringDllPath}");
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
                    Console.WriteLine("成功加载 Siemens.Engineering.dll");
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
    }
} 