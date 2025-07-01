"""
Главный интерфейс для системы обработки сертификатов
Запускает все скрипты последовательно или по отдельности
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

class CertificateProcessorInterface:
    def __init__(self):
        self.base_dir = Path.cwd()
        self.scripts = {
            '1': {
                'name': '1.new2.py',
                'description': 'Обработка PDF сертификатов (OCR)',
                'details': 'Извлекает ФИО и программы из PDF, сортирует по папкам'
            },
            '2': {
                'name': '2.folder_cleanup.py', 
                'description': 'Очистка названий папок',
                'details': 'Исправляет названия папок с программами'
            },
            '3': {
                'name': '3.sunder.py',
                'description': 'Объединение похожих папок',
                'details': 'Объединяет папки с похожими программами'
            },
            '4': {
                'name': '4.FIO.py',
                'description': 'Исправление ФИО в именах файлов',
                'details': 'Приводит ФИО к правильному виду'
            }
        }
        
        self.session_log = []
    
    def check_script_exists(self, script_name):
        """Проверяет существование скрипта"""
        script_path = self.base_dir / script_name
        return script_path.exists()
    
    def check_dependencies(self):
        """Проверяет зависимости и структуру папок"""
        print("🔍 Проверка готовности системы...")
        
        issues = []
        
        # Проверяем скрипты
        for script_info in self.scripts.values():
            if not self.check_script_exists(script_info['name']):
                issues.append(f"❌ Скрипт {script_info['name']} не найден")
        
        # Проверяем папки
        input_dir = self.base_dir / "input"
        if not input_dir.exists():
            issues.append("❌ Папка 'input' не найдена")
        else:
            pdf_files = list(input_dir.glob("*.pdf"))
            if not pdf_files:
                issues.append("  В папке 'input' нет PDF файлов")
            else:
                print(f" Найдено {len(pdf_files)} PDF файлов в папке 'input'")
        
        # Проверяем Python пакеты (основные)
        required_packages = ['pandas', 'pathlib', 'cv2', 'easyocr', 'pdf2image']
        for package in required_packages:
            try:
                if package == 'cv2':
                    import cv2
                elif package == 'easyocr':
                    import easyocr
                elif package == 'pdf2image':
                    import pdf2image
                elif package == 'pandas':
                    import pandas
                else:
                    __import__(package)
            except ImportError:
                issues.append(f"  Пакет {package} не установлен")
        
        if issues:
            print("\n🚨 Обнаружены проблемы:")
            for issue in issues:
                print(f"   {issue}")
            print("\n💡 Рекомендации:")
            print("   - Убедитесь, что все 4 скрипта находятся в текущей папке")
            print("   - Создайте папку 'input' и поместите туда PDF файлы")
            print("   - Установите необходимые пакеты: pip install pandas opencv-python easyocr pdf2image")
            return False
        else:
            print(" Система готова к работе!")
            return True
    
    def run_script(self, script_name, description):
        """Запускает отдельный скрипт"""
        script_path = self.base_dir / script_name
        
        print(f"\n Запуск: {description}")
        print(f"📄 Скрипт: {script_name}")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Запускаем скрипт в том же интерпретаторе Python
            result = subprocess.run([sys.executable, str(script_path)], 
                                  capture_output=False, 
                                  text=True, 
                                  cwd=self.base_dir)
            
            elapsed_time = time.time() - start_time
            
            if result.returncode == 0:
                status = " УСПЕШНО"
                self.session_log.append({
                    'script': script_name,
                    'status': 'SUCCESS',
                    'time': elapsed_time,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
            else:
                status = " ОШИБКА"
                self.session_log.append({
                    'script': script_name,
                    'status': 'ERROR',
                    'time': elapsed_time,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
            
            print("=" * 60)
            print(f"{status} | Время: {elapsed_time:.1f} сек")
            
            return result.returncode == 0
            
        except Exception as e:
            print(f" Критическая ошибка: {e}")
            self.session_log.append({
                'script': script_name,
                'status': 'CRITICAL_ERROR',
                'time': time.time() - start_time,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'error': str(e)
            })
            return False
    
    def run_all_scripts(self):
        """Запускает все скрипты последовательно"""
        print("\n ПОЛНАЯ ОБРАБОТКА СЕРТИФИКАТОВ")
        print("=" * 60)
        print("Будут выполнены все этапы:")
        print("1  Обработка PDF → извлечение данных")
        print("2  Очистка названий папок")
        print("3  Объединение похожих папок")  
        print("4  Исправление ФИО в файлах")
        print("=" * 60)
        print(" Запуск обработки...")
        
        start_time = time.time()
        successful_scripts = 0
        
        for script_num, script_info in self.scripts.items():
            print(f"\n ЭТАП {script_num}/4")
            
            success = self.run_script(script_info['name'], script_info['description'])
            
            if success:
                successful_scripts += 1
                print(f" Этап {script_num} завершен успешно")
            else:
                print(f" Этап {script_num} завершен с ошибкой")
                
                if script_num == '1':  # Если первый скрипт не удался
                    print(" Обработка PDF не удалась. Остальные этапы могут быть неактуальны.")
            
            # Пауза между этапами
            if script_num != '4':
                time.sleep(1)
        
        total_time = time.time() - start_time
        
        print("\n" + "=" * 60)
        print(f" ПОЛНАЯ ОБРАБОТКА ЗАВЕРШЕНА")
        print(f"⏱  Общее время: {total_time/60:.1f} минут")
        print(f" Успешных этапов: {successful_scripts}/4")
        
        if successful_scripts == 4:
            print(" Все этапы выполнены успешно!")
            print(" Результаты находятся в папке 'сертификаты'")
        else:
            print("  Некоторые этапы завершились с ошибками")
        
        self.show_session_summary()
    
    def show_session_summary(self):
        """Показывает сводку сессии"""
        if not self.session_log:
            return
            
        print(f"\n СВОДКА СЕССИИ:")
        print("-" * 40)
        
        for entry in self.session_log:
            status_icon = {
                'SUCCESS': 'Yspex',
                'ERROR': 'error', 
                'CRITICAL_ERROR': '!!!!error'
            }.get(entry['status'], '?')
            
            print(f"{status_icon} {entry['timestamp']} | {entry['script']} | {entry['time']:.1f}с")
    
    def show_menu(self):
        """Показывает главное меню"""
        while True:
            print("\n" + "=" * 60)
            print("            СИСТЕМА ОБРАБОТКИ СЕРТИФИКАТОВ")
            print("=" * 60)
            print("     БЫСТРЫЕ ДЕЙСТВИЯ:")
            print("     0  Полная обработка (все этапы)")
            print("     9  Проверить готовность системы")
            print()
            print(" ОТДЕЛЬНЫЕ ЭТАПЫ:")
            
            for num, info in self.scripts.items():
                status = "_" if self.check_script_exists(info['name']) else "X"
                print(f"   {num} {status} {info['description']}")
                print(f"       {info['details']}")
            
            print()
            print("   q Выход")
            print("-" * 60)
            
            choice = input("Выберите действие: ").strip().lower()
            
            if choice == 'q' or choice == 'quit' or choice == 'выход':
                print(" До свидания!")
                break
                
            elif choice == '0':
                if self.check_dependencies():
                    self.run_all_scripts()
                else:
                    input("\n Исправьте проблемы и нажмите Enter...")
                    
            elif choice == '9':
                self.check_dependencies()
                input("\n Нажмите Enter для продолжения...")
                
            elif choice in self.scripts:
                script_info = self.scripts[choice]
                if self.check_script_exists(script_info['name']):
                    self.run_script(script_info['name'], script_info['description'])
                else:
                    print(f" Скрипт {script_info['name']} не найден!")
                input("\n Нажмите Enter для продолжения...")
                
            else:
                print(" Неверный выбор! Попробуйте еще раз.")
                time.sleep(1)

def main():
    """Главная функция"""
    print(" Инициализация системы обработки сертификатов...")
    
    try:
        interface = CertificateProcessorInterface()
        interface.show_menu()
    except KeyboardInterrupt:
        print("\n\n Прервано пользователем")
    except Exception as e:
        print(f"\n Критическая ошибка: {e}")
        input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    main()