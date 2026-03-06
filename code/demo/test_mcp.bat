@echo off
chcp 65001 >nul
echo ========================================
echo 🚀 启动带 MCP 功能的 RAG 智能助手
echo ========================================
echo.

cd /d "%~dp0"
python rag_with_mcp.py

pause
