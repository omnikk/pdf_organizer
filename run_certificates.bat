REM Проверяем main.py
if not exist "main.py" (
    echo  Файл main.py не найден!
    echo  Убедитесь, что все файлы находятся в одной папке
    pause
    exit /b 1
)

echo  Все файлы найдены
echo.
echo  Запуск интерактивного интерфейса...
echo.

REM Запускаем main.py
python main.py

REM Проверяем результат
if errorlevel 1 (
    echo.
    echo  Программа завершилась с ошибкой
) else (
    echo.
    echo  Программа завершилась успешно
)

echo.
echo ===============================================
pause