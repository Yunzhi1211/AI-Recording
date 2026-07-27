@echo off
chcp 65001 >nul
echo ========================================
echo   培训视频自动生成工具 v1.0
echo ========================================
echo.

echo [0/5] 环境检查...
python 00_init_check.py
if errorlevel 1 goto error

echo.
echo [1/5] 转换PPT为图片...
python 01_convert_ppt_to_images.py
if errorlevel 1 goto error

echo.
echo [2/5] 提交语音合成任务...
python 02_submit.py
if errorlevel 1 goto error

echo.
echo [3/5] 等待并下载音频和时间戳...
python 03_query.py
if errorlevel 1 goto error

echo.
echo [4/5] 生成精确翻页时间表...
python 04_generate_slide_timings.py
if errorlevel 1 goto error

echo.
echo [5/5] 合成最终视频...
python 05_create_video_ffmpeg.py
if errorlevel 1 goto error

echo.
echo ========================================
echo   ✅ 全部完成！视频已生成！
echo   输出文件: output_video_ffmpeg.mp4
echo ========================================
pause
exit

:error
echo.
echo ❌ 执行失败，请检查错误信息。
pause
exit