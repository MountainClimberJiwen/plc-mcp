using System;
using MyFirstApp.Config;

namespace MyFirstApp
{
    class ConfigTest
    {
        static void Main2(string[] args)
        {
            try
            {
                Console.WriteLine("开始测试配置文件加载...");
                
                // 测试配置加载
                var config = AppConfig.Load();
                if (config == null)
                {
                    Console.WriteLine("配置加载失败：配置文件不存在或格式错误");
                    return;
                }

                // 打印配置信息
                Console.WriteLine("\n当前配置信息：");
                Console.WriteLine($"TIA Portal 路径: {config.TiaPortalPath}");
                Console.WriteLine($"Engineering DLL 路径: {config.EngineeringDllPath}");
                Console.WriteLine($"项目路径: {config.ProjectPath}");

                // 验证路径是否存在
                Console.WriteLine("\n验证路径：");
                Console.WriteLine($"TIA Portal 路径存在: {System.IO.Directory.Exists(config.TiaPortalPath)}");
                Console.WriteLine($"Engineering DLL 文件存在: {System.IO.File.Exists(config.EngineeringDllPath)}");
                Console.WriteLine($"项目文件存在: {System.IO.File.Exists(config.ProjectPath)}");

                Console.WriteLine("\n配置测试完成！");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"\n测试过程中发生错误：");
                Console.WriteLine($"错误信息: {ex.Message}");
                Console.WriteLine($"堆栈跟踪: {ex.StackTrace}");
            }

            Console.WriteLine("\n按任意键退出...");
            Console.ReadKey();
        }
    }
} 