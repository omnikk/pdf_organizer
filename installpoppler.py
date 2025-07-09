import os
import sys
import subprocess
import requests
import zipfile
from pathlib import Path
import json

def check_admin():
    """Проверяет права администратора"""
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def install_with_winget():
    """Пытается установить через winget"""
    print(" Попытка установки через winget...")
    
    try:
        result = subprocess.run(['winget', 'install', '--id=poppler.poppler'], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("Poppler установлен через winget!")
            return True
        else:
            print(f" Ошибка winget: {result.stderr}")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print(" winget недоступен")
        return False

def download_poppler():
    """Скачивает Poppler вручную"""
    print(" Ручная установка Poppler...")
    
    # URL последнего релиза
    api_url = "https://api.github.com/repos/oschwartz10612/poppler-windows/releases/latest"
    
    try:
        print(" Получение информации о последней версии...")
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        release_data = response.json()
        
        # Ищем ZIP файл
        download_url = None
        for asset in release_data['assets']:
            if asset['name'].endswith('.zip') and 'Release' in asset['name']:
                download_url = asset['browser_download_url']
                filename = asset['name']
                break
        
        if not download_url:
            print(" Не найден файл для скачивания")
            return False
        
        print(f" Скачивание {filename}...")
        
        # Скачиваем
        response = requests.get(download_url, timeout=300)
        response.raise_for_status()
        
        # Сохраняем во временную папку
        temp_dir = Path.home() / "Downloads"
        zip_path = temp_dir / filename
        
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        print(f"Файл сохранен: {zip_path}")
        
        # Распаковываем
        poppler_dir = Path("C:/poppler")
        
        print(f" Распаковка в {poppler_dir}...")
        
        # Создаем папку (может потребовать прав админа)
        try:
            poppler_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(" Нужны права администратора для записи в C:/")
            print(" Запустите PowerShell от имени администратора и повторите")
            return False
        
        # Распаковываем
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(poppler_dir)
        
        print(" Poppler распакован")
        
        # Удаляем ZIP
        zip_path.unlink()
        
        return True
        
    except Exception as e:
        print(f" Ошибка скачивания: {e}")
        return False

def add_to_path():
    """Добавляет Poppler в PATH"""
    print(" Добавление в PATH...")
    
    poppler_bin = Path("C:/poppler/Library/bin")
    
    if not poppler_bin.exists():
        # Ищем где находится bin
        possible_paths = [
            Path("C:/poppler/bin"),
            Path("C:/poppler/Library/bin"),
        ]
        
        # Ищем в подпапках
        for root in Path("C:/poppler").rglob("*"):
            if root.name == "bin" and (root / "pdftoppm.exe").exists():
                poppler_bin = root
                break
        
        if not poppler_bin.exists():
            print(" Не найден bin/pdftoppm.exe")
            print(" Проверьте содержимое C:/poppler/")
            return False
    
    poppler_bin_str = str(poppler_bin)
    
    # Проверяем, есть ли уже в PATH
    current_path = os.environ.get('PATH', '')
    if poppler_bin_str in current_path:
        print(" Poppler уже в PATH")
        return True
    
    try:
        # Добавляем в PATH для текущей сессии
        os.environ['PATH'] = poppler_bin_str + os.pathsep + current_path
        
        # Пытаемся добавить постоянно (может не сработать без админ прав)
        if sys.platform == "win32":
            import winreg
            
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                    current_user_path = winreg.QueryValueEx(key, "PATH")[0]
                    if poppler_bin_str not in current_user_path:
                        new_path = poppler_bin_str + os.pathsep + current_user_path
                        winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
                        print(" Poppler добавлен в PATH пользователя")
                    else:
                        print(" Poppler уже в PATH пользователя")
                        
            except Exception as e:
                print(f" Не удалось добавить в PATH автоматически: {e}")
                print(" Добавьте вручную через Панель управления")
                return False
        
        return True
        
    except Exception as e:
        print(f" Ошибка добавления в PATH: {e}")
        return False

def test_poppler():
    """Тестирует работу Poppler"""
    print(" Тестирование Poppler...")
    
    try:
        result = subprocess.run(['pdftoppm', '-h'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 or 'pdftoppm' in result.stderr:
            print(" Poppler работает!")
            return True
        else:
            print(" Poppler не отвечает")
            return False
            
    except FileNotFoundError:
        print(" pdftoppm не найден в PATH")
        return False
    except Exception as e:
        print(f" Ошибка тестирования: {e}")
        return False

def main():
    """Главная функция установки"""
    print(" АВТОМАТИЧЕСКИЙ УСТАНОВЩИК POPPLER")
    print("=" * 50)
    
    try:
        # Способ 1: winget
        if install_with_winget():
            if test_poppler():
                print("\n POPPLER УСТАНОВЛЕН УСПЕШНО!")
                return
        
        # Способ 2: ручная установка
        print("\nПереходим к ручной установке...")
        
        if download_poppler():
            if add_to_path():
                if test_poppler():
                    print("\n POPPLER УСТАНОВЛЕН УСПЕШНО!")
                    print(" Перезапустите PowerShell/CMD для применения PATH")
                    return
        
        # Если не получилось
        print("\n АВТОМАТИЧЕСКАЯ УСТАНОВКА НЕ УДАЛАСЬ")
        print("\n РУЧНАЯ УСТАНОВКА:")
        print("1. Скачайте: https://github.com/oschwartz10612/poppler-windows/releases/latest")
        print("2. Найдите файл Release-xx.xx.x-0.zip")
        print("3. Распакуйте в C:\\poppler\\")
        print("4. Добавьте в PATH: C:\\poppler\\Library\\bin")
        print("5. Перезапустите PowerShell")

    except KeyboardInterrupt:
        print("\n\n Установка прервана пользователем")
    except Exception as e:
        print(f"\n\n Неожиданная ошибка: {e}")
    finally:
        print("\n" + "=" * 50)
        print("Для выхода нажмите Enter...")
        input()

if __name__ == "__main__":
    main()