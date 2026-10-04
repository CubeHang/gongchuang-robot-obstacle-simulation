@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ================ 1/4 地图与最短路径校验 ================
python tools\verify_sim.py || goto :fail
echo.
echo ================ 2/4 界面流程冒烟测试 ================
python tools\smoke_gui.py || goto :fail
echo.
echo ================ 3/4 画布绘制内容检查 ================
python tools\check_draw.py || goto :fail
echo.
echo ================ 4/4 路径效果图渲染与像素校验 ================
python tools\render_preview.py || goto :fail
python tools\verify_render.py || goto :fail
echo.
echo 全部自检通过。
pause
exit /b 0
:fail
echo.
echo 自检失败，请查看上面的输出。
pause
exit /b 1
