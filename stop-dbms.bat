@echo off
title Stop Semantic PYQ Analyzer

echo =====================================================================
echo    STOPPING SEMANTIC PYQ ANALYZER & STUDY HEATMAP
echo =====================================================================
echo.
echo Stopping application containers (pyq_frontend, pyq_backend, pyq_db)...
echo Note: PostgreSQL data volume and uploaded files will be safely preserved.
echo.

docker compose stop

echo.
echo =====================================================================
echo    ALL CONTAINERS STOPPED SAFELY
echo =====================================================================
echo.
echo Your PostgreSQL database records and uploaded files are preserved intact.
echo To start the project again at any time, double-click start-dbms.bat.
echo.
pause
