using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;
using System.ComponentModel;
using System.Threading.Tasks;

namespace Web
{
    public class Program
    {
        public static async Task Main(string[] args)
        {
            var builder = Host.CreateApplicationBuilder(args);
            builder.Logging.AddConsole(consoleLogOptions =>
            {
                // Configure all logs to go to stderr
                consoleLogOptions.LogToStandardErrorThreshold = LogLevel.Trace;
            });
            
            // 添加HTTP健康检查服务器
            builder.Services.AddSingleton<PLCWebServer>();
            
            builder.Services
                .AddMcpServer()
                .WithStdioServerTransport()
                .WithToolsFromAssembly();
                
            var host = builder.Build();
            
            // 启动HTTP服务器
            var plcServer = host.Services.GetRequiredService<PLCWebServer>();
            var logger = host.Services.GetRequiredService<ILogger<Program>>();
            
            logger.LogInformation("正在启动HTTP健康检查服务器...");
            
            // 在后台启动HTTP服务器
            _ = Task.Run(async () =>
            {
                try
                {
                    await plcServer.StartAsync();
                }
                catch (System.Exception ex)
                {
                    logger.LogError(ex, "HTTP服务器启动失败");
                }
            });
            
            await host.RunAsync();
        }
    }

    [McpServerToolType]
    public static class EchoTool
    {
        [McpServerTool, Description("Echoes the message back to the client.")]
        public static string Echo(string message) => $"hello {message}";
    }
}