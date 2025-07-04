import os
import re
import shutil
from pathlib import Path

class FolderCleanup:
    def __init__(self):
        self.base_dir = Path.cwd()
        self.certificates_dir = self.base_dir / "сертификаты"
    
    def clean_program_name(self, name):
        """Очищает название программы от мусора"""
        if not name:
            return ""
        
        # Убираем лишние символы
        name = re.sub(r'["\u201C\u201D«»()_]', '', name)
        name = re.sub(r'\s+', ' ', name)
        name = name.strip()
        
        # Убираем фразы "в объёме", "в объеме" и цифры после них
        name = re.sub(r'\s*[вВ]\s*объ[её]ме.*$', '', name)
        name = re.sub(r'\s*\d+\s*час.*$', '', name)
        name = re.sub(r'\s*обьёме.*$', '', name)
        name = re.sub(r'\s*объёмс.*$', '', name)
        name = re.sub(r'\s*объёне.*$', '', name)
        
        # Исправляем часто встречающиеся ошибки OCR
        replacements = [
            (r'^[0(]\s*', 'О '),  # "0 контрактной" -> "О контрактной"
            (r'коптрактной', 'контрактной'),
            (r'систем[се]', 'системе'),
            (r'закупок[ъэ]', 'закупок'),
            (r'Государствен[а-я]*', 'Государственные'),
            (r'муниципальн[а-я]*', 'муниципальные'),
            (r'контрактн[а-я]*', 'контрактной'),
            (r'44-Ф[З3]', '44-ФЗ'),
            (r'практика[а-я]*', 'практика'),
            (r'теория\s+и\s+практика[а-я]*', 'теория и практика'),
        ]
        
        for pattern, replacement in replacements:
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)
        
        # Нормализуем пробелы
        name = re.sub(r'\s+', ' ', name)
        
        # Убираем лишние символы в конце
        name = re.sub(r'[\*\#\{\}\[\]\$\%\@\!\+\=\<\>]+.*$', '', name)
        
        return name.strip()
    
    def get_standard_program_name(self, dirty_name):
        """Возвращает стандартизированное название программы"""
        cleaned = self.clean_program_name(dirty_name).lower()
        
        # Стандартные названия программ
        if 'государственные' in cleaned and 'муниципальные' in cleaned and 'закупки' in cleaned:
            if '44-фз' in cleaned or 'теория и практика' in cleaned:
                return "Государственные и муниципальные закупки (44-ФЗ) - теория и практика"
        
        if 'контрактной системе' in cleaned and 'сфере закупок' in cleaned:
            return "О контрактной системе в сфере закупок"
        
        # Если не нашли стандартное название, возвращаем очищенное
        return self.clean_program_name(dirty_name)
    
    def rename_folders(self):
        """Переименовывает папки с программами"""
        if not self.certificates_dir.exists():
            print("[ERROR] Папка 'сертификаты' не найдена!")
            return
        
        program_folders = [d for d in self.certificates_dir.iterdir() 
                          if d.is_dir() and d.name != "Неопознанные"]
        
        if not program_folders:
            print("[FOLDER] Папки с программами не найдены!")
            return
        
        print(f"[CHECK] Найдено {len(program_folders)} папок с программами:")
        print("=" * 60)
        
        renamed_count = 0
        
        for folder in program_folders:
            old_name = folder.name
            new_name = self.get_standard_program_name(old_name)
            
            print(f"\n[DIR] Папка: '{old_name}'")
            
            if old_name == new_name:
                print(f"   [OK] Название уже корректное")
                continue
            
            print(f"   [PROCESS] Новое название: '{new_name}'")
            
            # Создаем безопасное имя для файловой системы
            safe_new_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)
            new_path = self.certificates_dir / safe_new_name
            
            # Проверяем, не существует ли уже папка с таким именем
            if new_path.exists() and new_path != folder:
                print(f"   [WARNING]  Папка с названием '{safe_new_name}' уже существует!")
                
                # Перемещаем файлы в существующую папку
                files_moved = 0
                for file in folder.glob("*.pdf"):
                    target_file = new_path / file.name
                    if not target_file.exists():
                        shutil.move(file, target_file)
                        files_moved += 1
                    else:
                        # Добавляем счетчик к имени файла
                        counter = 1
                        while True:
                            name_part = file.stem
                            ext_part = file.suffix
                            new_file_name = f"{name_part}_{counter}{ext_part}"
                            target_file = new_path / new_file_name
                            if not target_file.exists():
                                shutil.move(file, target_file)
                                files_moved += 1
                                break
                            counter += 1
                
                print(f"   [FOLDER] Перемещено {files_moved} файлов в существующую папку")
                
                # Удаляем пустую папку
                try:
                    folder.rmdir()
                    print(f"   [DELETE]  Удалена пустая папка")
                    renamed_count += 1
                except OSError:
                    print(f"   [ERROR] Не удалось удалить папку (возможно, не пустая)")
            else:
                # Просто переименовываем папку
                try:
                    folder.rename(new_path)
                    print(f"   [OK] Папка переименована")
                    renamed_count += 1
                except OSError as e:
                    print(f"   [ERROR] Ошибка переименования: {e}")
        
        print(f"\n[SUCCESS] ИТОГО:")
        print(f"   [OK] Обработано папок: {renamed_count}")
        print(f"   [FOLDER] Всего папок: {len(program_folders)}")
    
    def show_current_folders(self):
        """Показывает текущие папки с программами"""
        if not self.certificates_dir.exists():
            print("[ERROR] Папка 'сертификаты' не найдена!")
            return
        
        program_folders = [d for d in self.certificates_dir.iterdir() 
                          if d.is_dir() and d.name != "Неопознанные"]
        
        if not program_folders:
            print("[FOLDER] Папки с программами не найдены!")
            return
        
        print(f"[FOLDER] Текущие папки с программами ({len(program_folders)}):")
        print("=" * 60)
        
        for i, folder in enumerate(program_folders, 1):
            file_count = len(list(folder.glob("*.pdf")))
            print(f"{i:2}. {folder.name} ({file_count} файлов)")
            
            # Показываем, что будет предложено как новое название
            new_name = self.get_standard_program_name(folder.name)
            if new_name != folder.name:
                print(f"    [TIP] Предлагается: '{new_name}'")

def main():
    cleanup = FolderCleanup()
    print("" + "="*60)
    print("           АВТОМАТИЧЕСКАЯ ОЧИСТКА НАЗВАНИЙ ПАПОК")
    print("="*60)
    print("Запущено через GUI - автоматическое переименование...")
    cleanup.rename_folders()

if __name__ == "__main__":
    main()