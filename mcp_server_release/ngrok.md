npx -y supergateway  --stdio "dotnet run --project E:\\pycharm-projects\\tia-openness\\mcp_server\\mcp_server.csproj" --port 8000 --baseUrl http://localhost:8000  --ssePath /sse

C:\Users\Administrator\AppData\Local/ngrok/ngrok.yml

#  .\mcp_server\ngrok.exe config add-authtoken 2lERWpl8scvGWpGxNlCNSsVqGhm_3QteHWZbLLxYWq1qdheNK

.\mcp_server\ngrok.exe http 8000


dotnet run --project web/web.csproj

cd E://pycharm-projects/tia-openness/web/bin/Release/net48 && Start-Process -FilePath "web.exe" -WindowStyle Hidden
