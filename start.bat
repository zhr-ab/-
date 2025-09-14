@echo off
echo 正在安装依赖...
pip install -r requirements.txt

echo.
echo 启动文件管理器服务器...
echo 访问地址: http://localhost:8000
echo 按 Ctrl+C 停止服务器
echo.

python server.py

pause