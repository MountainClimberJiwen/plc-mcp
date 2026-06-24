using Microsoft.Extensions.Logging;
using System;
using System.IO;
using System.Net;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System;
using System.Linq;
using System.Collections.Generic;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
using Siemens.Engineering.HW.Utilities;
using Siemens.Engineering.SW;
using System.IO;
using Siemens.Engineering.SW.Types;
using Siemens.Engineering.SW.Tags;
using Siemens.Engineering.SW.Blocks;
using Siemens.Engineering.Compiler;
using Web;
using Web.Config;
using System.Net.Http;

namespace Web
{
    public class PLCWebServer
    {
        private readonly ILogger<PLCWebServer> _logger;
        private readonly int _port;
        private readonly HttpListener _listener;
        private bool _isRunning;

        public PLCWebServer(ILogger<PLCWebServer> logger, int port = 8080)
        {
            _logger = logger;
            _port = port;
            _listener = new HttpListener();
            _listener.Prefixes.Add($"http://localhost:{port}/");
        }

        public async Task StartAsync()
        {
            try
            {
                _listener.Start();
                _isRunning = true;
                _logger.LogInformation("HTTP服务器已启动，监听端口 {Port}", _port);

                while (_isRunning)
                {
                    try
                    {
                        var context = await _listener.GetContextAsync();
                        _ = Task.Run(() => HandleRequestAsync(context));
                    }
                    catch (Exception ex)
                    {
                        if (_isRunning)
                        {
                            _logger.LogError(ex, "处理请求时发生错误");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "启动HTTP服务器失败");
                throw;
            }
        }

        public void Stop()
        {
            _isRunning = false;
            _listener.Stop();
            _listener.Close();
            _logger.LogInformation("HTTP服务器已停止");
        }

        private async Task HandleRequestAsync(HttpListenerContext context)
        {
            var request = context.Request;
            var response = context.Response;
            var path = request.Url.AbsolutePath.ToLower();

            try
            {
                _logger.LogInformation("收到请求: {Method} {Path}", request.HttpMethod, path);

                switch (path)
                {
                    case "/ping":
                        await HandleUpdateSclAsync(response, context);
                        break;
                    case "/update_scl":
                        await HandleUpdateSclAsync(response, context);
                        break;
                    case "/status":
                        await HandleStatusAsync(response);
                        break;
                    case "/":
                        await HandleRootAsync(response);
                        break;
                    default:
                        await HandleNotFoundAsync(response, path);
                        break;
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "处理请求时发生错误: {Path}", path);
                await HandleErrorAsync(response, ex);
            }
            finally
            {
                response.Close();
            }
        }

        private async Task HandlePingAsync(HttpListenerResponse response)
        {
            _logger.LogInformation("处理ping请求");
            
            var data = new
            {
                status = "ok",
                timestamp = DateTime.UtcNow,
                message = "pong"
            };
            
            await WriteJsonResponseAsync(response, data, 200);
        }

        private async Task HandleUpdateSclAsync(HttpListenerResponse response, HttpListenerContext context)
        {
            //  const url = `http://localhost:8000/ping?path=${encodeURIComponent(filePath)}`;
            // extract path from request
            var request = context.Request;
            var path = request.QueryString["path"];
            // plcName 'PLC1' extract from ' scl\PLC1\block_3.scl' 
            var plcName = path.Split('\\')[1];
            _logger.LogInformation("处理更新SCL请求: {path}", path);

            // string sclCodeDirPath = "scl/" + plcName;
            var config = AppConfig.Load();
            string sclCodeDirPath = Path.Combine(config.SclCodeRootDir ?? string.Empty, path);
            using (var tiaPortalProject = new TiaPortalProject(plcName, sclCodeDirPath, config))
            {
                tiaPortalProject.ProcessProject();
            }
          
             var data = new
            {
                status = "ok",
                timestamp = DateTime.UtcNow,
                message = "update scl success"
            };
            await WriteJsonResponseAsync(response, data, 200);
        }


        private async Task HandleRootAsync(HttpListenerResponse response)
        {
            _logger.LogInformation("处理根路径请求");
            
            var data = new
            {
                service = "Health Check Web Server",
                version = "1.0.0",
                endpoints = new[]
                {
                    "/ping - Health check endpoint",
                    "/health - Detailed health status",
                    "/status - Service status"
                },
                timestamp = DateTime.UtcNow
            };

            await WriteJsonResponseAsync(response, data, 200);
        }

        private async Task HandleHealthAsync(HttpListenerResponse response)
        {
            _logger.LogInformation("处理健康状态请求");
            
            var data = new
            {
                status = "healthy",
                timestamp = DateTime.UtcNow,
                memory = GC.GetTotalMemory(false)
            };

            await WriteJsonResponseAsync(response, data, 200);
        }

        private async Task HandleStatusAsync(HttpListenerResponse response)
        {
            _logger.LogInformation("处理状态请求");
            
            var data = new
            {
                service = "Health Check Web Server",
                status = "running",
                port = _port,
                timestamp = DateTime.UtcNow,
                environment = Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT") ?? "Production"
            };

            await WriteJsonResponseAsync(response, data, 200);
        }

        private async Task HandleNotFoundAsync(HttpListenerResponse response, string path)
        {
            _logger.LogWarning("处理404请求: {Path}", path);
            
            var data = new
            {
                error = "Not Found",
                message = $"路径 '{path}' 不存在",
                timestamp = DateTime.UtcNow,
                availableEndpoints = new[]
                {
                    "/ping",
                    "/health", 
                    "/status"
                }
            };

            await WriteJsonResponseAsync(response, data, 404);
        }

        private async Task HandleErrorAsync(HttpListenerResponse response, Exception ex)
        {
            var data = new
            {
                error = "Internal Server Error",
                message = ex.Message,
                timestamp = DateTime.UtcNow
            };

            await WriteJsonResponseAsync(response, data, 500);
        }

        private async Task WriteJsonResponseAsync(HttpListenerResponse response, object data, int statusCode)
        {
            var json = JsonSerializer.Serialize(data, new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase
            });

            var buffer = Encoding.UTF8.GetBytes(json);
            
            response.StatusCode = statusCode;
            response.ContentType = "application/json; charset=utf-8";
            response.ContentLength64 = buffer.Length;
            response.AddHeader("Access-Control-Allow-Origin", "*");
            response.AddHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
            response.AddHeader("Access-Control-Allow-Headers", "Content-Type");

            await response.OutputStream.WriteAsync(buffer, 0, buffer.Length);
        }
    }
}
