npx -y supergateway  --stdio "dotnet run --project E:\\pycharm-projects\\tia-openness\\mcp_server\\mcp_server.csproj" --port 8000 --baseUrl http://localhost:8000  --ssePath /sse

background:
Start-Process -FilePath "npx" -ArgumentList "-y", "supergateway", "--stdio", ".\mcp_server\bin\Release\net48\mcp_server.exe", "--port", "8000", "--baseUrl", "http://localhost:8000", "--ssePath", "/sse" -WindowStyle Hidden -WorkingDirectory "E:\pycharm-projects\tia-openness"


C:\Users\Administrator\AppData\Local/ngrok/ngrok.yml

#  .\mcp_server\ngrok.exe config add-authtoken <YOUR_NGROK_AUTHTOKEN>

.\mcp_server\ngrok.exe http 8000

Start-Job -ScriptBlock {
    npx -y supergateway --stdio "dotnet run --project E:\pycharm-projects\tia-openness\mcp_server\mcp_server.csproj" --port 8000 --baseUrl http://localhost:8000 --ssePath /sse
}

build & release:
cd E:\pycharm-projects\tia-openness; dotnet publish web/web.csproj -c Release -o web\publish

cd web/bin/Release/net48 && Start-Process -FilePath "web.exe" -WindowStyle Hidden