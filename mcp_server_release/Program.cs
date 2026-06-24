using System;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Serilog;
using McpServer.Config;
using Siemens.Engineering;
using TestServerWithHosting.Tools;
using ModelContextProtocol.Server;

namespace McpServer
{
    class Program
    {
        static void Main(string[] args)
        {
            try
            {
                // 加载配置
                var config = AppConfig.Load();
                if (config == null)
                {
                    Log.Information("配置加载失败：配置文件不存在或格式错误");
                }

                // 连接到TIA Portal
                Log.Information("\n连接到TIA Portal...");
                TiaPortal tiaPortal = null;
                var processes = TiaPortal.GetProcesses();
                if (processes.Count > 0)
                {
                    Log.Information("发现正在运行的TIA Portal实例，尝试连接...");
                    tiaPortal = processes[0].Attach();
                }
                else
                {
                    Log.Information("未发现运行中的TIA Portal实例，启动新实例...");
                    tiaPortal = new TiaPortal(TiaPortalMode.WithUserInterface);
                }

                Log.Information("Starting server...");

                var builder = Host.CreateApplicationBuilder(args);
                builder.Services.AddMcpServer()
                    .WithStdioServerTransport()
                    // .WithTools<SampleLlmTool>()
                    .WithTools<EchoTool>();
                    

                builder.Services.AddSingleton(_ =>
                {
                    var project = tiaPortal.Projects.Open(new System.IO.FileInfo("E:\\tia\\test\\test.ap19"));
                    return project;
                });

                var host = builder.Build();
                host.Run();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error: {ex.Message}");
                Console.WriteLine($"StackTrace: {ex.StackTrace}");
            }
        }
    }
}