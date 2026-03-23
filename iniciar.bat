@echo off
title Simulador de Threads - Inatel
chcp 65001 >nul

echo.
echo  ================================================
echo   Simulador de Threads - Cruzamento sem Mutex
echo  ================================================
echo.
echo  Iniciando servidor na porta 8001...
echo.

cd /d "%~dp0backend"
start "Servidor FastAPI - Threads" cmd /k "python -m uvicorn main:app --port 8001 --reload"

echo  Aguardando servidor inicializar...
timeout /t 3 /nobreak >nul

echo  Abrindo navegador...
start "" "%~dp0frontend\index.html"

echo.
echo  Servidor rodando em: http://localhost:8001
echo  Frontend aberto no navegador.
echo.
echo  Para encerrar: feche a janela "Servidor FastAPI".
echo.
timeout /t 4 /nobreak >nul
exit
