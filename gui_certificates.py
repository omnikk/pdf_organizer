"""
GUI интерфейс для системы обработки сертификатов
Современный графический интерфейс с прогресс-барами и логами
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import subprocess
import sys
import time
import os
import json
from pathlib import Path
from datetime import datetime
import queue

class CertificateProcessorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Система обработки сертификатов")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Стиль
        self.setup_styles()
        
        # Переменные
        self.base_dir = Path.cwd()
        self.is_processing = False
        self.current_process = None
        self.log_queue = queue.Queue()
        
        # Данные о скриптах
        self.scripts = {
            '1': {
                'name': '1.new2.py',
                'title': 'Обработка PDF сертификатов',
                'description': 'Извлекает ФИО и программы из PDF файлов\nСортирует по папкам с помощью OCR',
                'icon': '📄',
                'color': '#4CAF50'
            },
            '2': {
                'name': '2.folder_cleanup.py', 
                'title': 'Очистка названий папок',
                'description': 'Исправляет и стандартизирует\nназвания папок с программами',
                'icon': '🗂️',
                'color': '#2196F3'
            },
            '3': {
                'name': '3.sunder.py',
                'title': 'Объединение похожих папок',
                'description': 'Находит и объединяет папки\nс похожими программами',
                'icon': '🔗',
                'color': '#FF9800'
            },
            '4': {
                'name': '4.FIO.py',
                'title': 'Исправление ФИО в файлах',
                'description': 'Приводит имена файлов с ФИО\nк правильному виду',
                'icon': '👤',
                'color': '#9C27B0'
            }
        }
        
        # Создаем интерфейс
        self.create_widgets()
        self.check_system_ready()
        
        # Запускаем обработку очереди логов
        self.process_log_queue()
    
    def setup_styles(self):
        """Настройка стилей"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Стиль для больших кнопок
        style.configure('Large.TButton', font=('Arial', 11, 'bold'))
        style.configure('Action.TButton', font=('Arial', 12, 'bold'))
        
        # Стиль для прогресс-бара
        style.configure('Custom.Horizontal.TProgressbar', 
                       troughcolor='#E0E0E0', 
                       background='#4CAF50')
    
    def create_widgets(self):
        """Создает все виджеты интерфейса"""
        # Главная рамка
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Настройка сетки
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Заголовок
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        title_label = tk.Label(title_frame, 
                              text="🎓 Система обработки сертификатов", 
                              font=('Arial', 18, 'bold'),
                              fg='#1976D2')
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, 
                                 text="Автоматическая обработка PDF сертификатов с OCR и сортировкой",
                                 font=('Arial', 10),
                                 fg='#666666')
        subtitle_label.pack()
        
        # Левая панель - кнопки управления
        left_frame = ttk.LabelFrame(main_frame, text="Управление", padding="10")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Кнопки быстрых действий
        quick_frame = ttk.LabelFrame(left_frame, text="Быстрые действия", padding="5")
        quick_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.full_process_btn = tk.Button(quick_frame, 
                                         text="🚀 ПОЛНАЯ ОБРАБОТКА",
                                         font=('Arial', 12, 'bold'),
                                         bg='#4CAF50', fg='white',
                                         height=2,
                                         command=self.run_full_process)
        self.full_process_btn.pack(fill=tk.X, pady=2)
        
        self.check_system_btn = tk.Button(quick_frame,
                                         text="🔍 Проверить систему",
                                         font=('Arial', 10),
                                         bg='#2196F3', fg='white',
                                         command=self.check_system_detailed)
        self.check_system_btn.pack(fill=tk.X, pady=2)
        
        # Отдельные этапы
        stages_frame = ttk.LabelFrame(left_frame, text="Отдельные этапы", padding="5")
        stages_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stage_buttons = {}
        for script_id, script_info in self.scripts.items():
            btn_frame = tk.Frame(stages_frame)
            btn_frame.pack(fill=tk.X, pady=2)
            
            btn = tk.Button(btn_frame,
                           text=f"{script_info['icon']} {script_info['title']}",
                           font=('Arial', 9, 'bold'),
                           bg=script_info['color'], fg='white',
                           height=2,
                           command=lambda sid=script_id: self.run_single_script(sid))
            btn.pack(fill=tk.X)
            
            # Описание
            desc_label = tk.Label(btn_frame, 
                                 text=script_info['description'],
                                 font=('Arial', 8),
                                 fg='#666666',
                                 justify=tk.LEFT)
            desc_label.pack(fill=tk.X)
            
            self.stage_buttons[script_id] = btn
        
        # Настройки
        settings_frame = ttk.LabelFrame(left_frame, text="Настройки", padding="5")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_cb = ttk.Checkbutton(settings_frame, 
                                        text="Автопрокрутка логов",
                                        variable=self.auto_scroll_var)
        auto_scroll_cb.pack(anchor=tk.W)
        
        # Кнопки управления процессом
        control_frame = ttk.LabelFrame(left_frame, text="Управление процессом", padding="5")
        control_frame.pack(fill=tk.X)
        
        self.stop_btn = tk.Button(control_frame,
                                 text="⏹️ Остановить",
                                 font=('Arial', 10, 'bold'),
                                 bg='#F44336', fg='white',
                                 state=tk.DISABLED,
                                 command=self.stop_process)
        self.stop_btn.pack(fill=tk.X, pady=2)
        
        self.clear_logs_btn = tk.Button(control_frame,
                                       text="🗑️ Очистить логи",
                                       font=('Arial', 9),
                                       bg='#757575', fg='white',
                                       command=self.clear_logs)
        self.clear_logs_btn.pack(fill=tk.X, pady=2)
        
        # Правая панель - логи и прогресс
        right_frame = ttk.LabelFrame(main_frame, text="Выполнение", padding="10")
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        
        # Статус и прогресс
        status_frame = ttk.Frame(right_frame)
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        
        tk.Label(status_frame, text="Статус:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W)
        self.status_label = tk.Label(status_frame, text="Готов к работе", 
                                    font=('Arial', 10), fg='#4CAF50')
        self.status_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Прогресс-бар
        tk.Label(status_frame, text="Прогресс:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W)
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate', style='Custom.Horizontal.TProgressbar')
        self.progress.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=(5, 0))
        
        # Логи
        logs_frame = ttk.LabelFrame(right_frame, text="Логи выполнения", padding="5")
        logs_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        logs_frame.columnconfigure(0, weight=1)
        logs_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(logs_frame, 
                                                 height=20, 
                                                 font=('Consolas', 9),
                                                 wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Тэги для раскраски логов
        self.log_text.tag_configure("success", foreground="#4CAF50", font=('Consolas', 9, 'bold'))
        self.log_text.tag_configure("error", foreground="#F44336", font=('Consolas', 9, 'bold'))
        self.log_text.tag_configure("warning", foreground="#FF9800", font=('Consolas', 9, 'bold'))
        self.log_text.tag_configure("info", foreground="#2196F3", font=('Consolas', 9, 'bold'))
        self.log_text.tag_configure("header", foreground="#9C27B0", font=('Consolas', 10, 'bold'))
        
        # Нижняя панель - статистика
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.stats_label = tk.Label(bottom_frame, 
                                   text="📁 Система готова к работе",
                                   font=('Arial', 9),
                                   fg='#666666')
        self.stats_label.pack(side=tk.LEFT)
        
        # Кнопка выбора папки
        self.select_folder_btn = tk.Button(bottom_frame,
                                          text="📂 Выбрать папку",
                                          font=('Arial', 9),
                                          command=self.select_base_folder)
        self.select_folder_btn.pack(side=tk.RIGHT)
    
    def log_message(self, message, tag="normal"):
        """Добавляет сообщение в очередь логов"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put((f"[{timestamp}] {message}", tag))
    
    def process_log_queue(self):
        """Обрабатывает очередь логов"""
        try:
            while True:
                message, tag = self.log_queue.get_nowait()
                
                # Добавляем в лог
                self.log_text.insert(tk.END, message + "\n", tag)
                
                # Автопрокрутка
                if self.auto_scroll_var.get():
                    self.log_text.see(tk.END)
                
        except queue.Empty:
            pass
        
        # Планируем следующую проверку
        self.root.after(100, self.process_log_queue)
    
    def update_status(self, status, color="#4CAF50"):
        """Обновляет статус"""
        self.status_label.config(text=status, fg=color)
    
    def check_system_ready(self):
        """Быстрая проверка готовности системы"""
        try:
            input_dir = self.base_dir / "input"
            if input_dir.exists():
                pdf_count = len(list(input_dir.glob("*.pdf")))
                if pdf_count > 0:
                    self.stats_label.config(text=f"📁 Найдено {pdf_count} PDF файлов в папке input")
                else:
                    self.stats_label.config(text="⚠️ В папке input нет PDF файлов")
            else:
                self.stats_label.config(text="❌ Папка input не найдена")
        except Exception as e:
            self.stats_label.config(text=f"❌ Ошибка проверки: {e}")
    
    def check_system_detailed(self):
        """Детальная проверка системы"""
        self.log_message("🔍 Запуск детальной проверки системы...", "header")
        
        def check_thread():
            try:
                # Проверка скриптов
                self.log_message("Проверка скриптов...")
                missing_scripts = []
                for script_info in self.scripts.values():
                    script_path = self.base_dir / script_info['name']
                    if script_path.exists():
                        self.log_message(f"✅ {script_info['name']}", "success")
                    else:
                        self.log_message(f"❌ {script_info['name']} не найден", "error")
                        missing_scripts.append(script_info['name'])
                
                # Проверка папок
                self.log_message("Проверка структуры папок...")
                input_dir = self.base_dir / "input"
                if input_dir.exists():
                    pdf_files = list(input_dir.glob("*.pdf"))
                    self.log_message(f"✅ Папка input найдена ({len(pdf_files)} PDF файлов)", "success")
                else:
                    self.log_message("❌ Папка input не найдена", "error")
                
                # Проверка библиотек
                self.log_message("Проверка библиотек...")
                required_libs = ['pandas', 'easyocr', 'pdf2image', 'cv2', 'numpy']
                for lib in required_libs:
                    try:
                        if lib == 'cv2':
                            import cv2
                        else:
                            __import__(lib)
                        self.log_message(f"✅ {lib}", "success")
                    except ImportError:
                        self.log_message(f"❌ {lib} не установлен", "error")
                
                if not missing_scripts:
                    self.log_message("🎉 Система готова к работе!", "success")
                else:
                    self.log_message("⚠️ Обнаружены проблемы", "warning")
                    
            except Exception as e:
                self.log_message(f"❌ Ошибка проверки: {e}", "error")
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def select_base_folder(self):
        """Выбор базовой папки"""
        folder = filedialog.askdirectory(title="Выберите папку с проектом")
        if folder:
            self.base_dir = Path(folder)
            self.log_message(f"📂 Установлена базовая папка: {folder}", "info")
            self.check_system_ready()
    
    def disable_buttons(self):
        """Отключает кнопки во время выполнения"""
        self.full_process_btn.config(state=tk.DISABLED)
        self.check_system_btn.config(state=tk.DISABLED)
        for btn in self.stage_buttons.values():
            btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
    
    def enable_buttons(self):
        """Включает кнопки после выполнения"""
        self.full_process_btn.config(state=tk.NORMAL)
        self.check_system_btn.config(state=tk.NORMAL)
        for btn in self.stage_buttons.values():
            btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def run_script_process(self, script_name, description):
        """Запускает скрипт в отдельном процессе"""
        script_path = self.base_dir / script_name
        
        if not script_path.exists():
            self.log_message(f"❌ Скрипт {script_name} не найден", "error")
            return False
        
        self.log_message(f"🚀 Запуск: {description}", "header")
        self.log_message(f"📄 Скрипт: {script_name}", "info")
        self.log_message("=" * 60)
        
        try:
            self.current_process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.base_dir,
                bufsize=1,
                universal_newlines=True
            )
            
            # Читаем вывод в реальном времени
            while True:
                output = self.current_process.stdout.readline()
                if output == '' and self.current_process.poll() is not None:
                    break
                if output:
                    # Определяем тег по содержимому
                    line = output.strip()
                    if "✅" in line or "успешно" in line.lower():
                        tag = "success"
                    elif "❌" in line or "ошибка" in line.lower():
                        tag = "error"
                    elif "⚠️" in line or "внимание" in line.lower():
                        tag = "warning"
                    elif "🎉" in line or "завершен" in line.lower():
                        tag = "success"
                    else:
                        tag = "normal"
                    
                    self.log_message(line, tag)
            
            return_code = self.current_process.wait()
            
            if return_code == 0:
                self.log_message("🎉 Скрипт выполнен успешно!", "success")
                return True
            else:
                self.log_message(f"❌ Скрипт завершился с ошибкой (код: {return_code})", "error")
                return False
                
        except Exception as e:
            self.log_message(f"❌ Критическая ошибка: {e}", "error")
            return False
    
    def run_single_script(self, script_id):
        """Запуск одного скрипта"""
        if self.is_processing:
            messagebox.showwarning("Внимание", "Уже выполняется обработка!")
            return
        
        script_info = self.scripts[script_id]
        
        def run_thread():
            self.is_processing = True
            self.disable_buttons()
            self.progress.start()
            self.update_status(f"Выполняется: {script_info['title']}", "#FF9800")
            
            try:
                success = self.run_script_process(script_info['name'], script_info['title'])
                
                if success:
                    self.update_status("Готов к работе", "#4CAF50")
                else:
                    self.update_status("Ошибка выполнения", "#F44336")
                    
            finally:
                self.is_processing = False
                self.progress.stop()
                self.enable_buttons()
                self.current_process = None
        
        threading.Thread(target=run_thread, daemon=True).start()
    
    def run_full_process(self):
        """Запуск полной обработки"""
        if self.is_processing:
            messagebox.showwarning("Внимание", "Уже выполняется обработка!")
            return
        
        result = messagebox.askyesno(
            "Полная обработка", 
            "Запустить полную обработку сертификатов?\n\n"
            "Будут выполнены все этапы:\n"
            "1. Обработка PDF (OCR)\n"
            "2. Очистка названий папок\n"
            "3. Объединение похожих папок\n"
            "4. Исправление ФИО в файлах\n\n"
            "Это может занять длительное время."
        )
        
        if not result:
            return
        
        def run_thread():
            self.is_processing = True
            self.disable_buttons()
            self.progress.start()
            self.update_status("Выполняется полная обработка...", "#FF9800")
            
            start_time = time.time()
            successful_stages = 0
            
            self.log_message("🚀 НАЧАЛО ПОЛНОЙ ОБРАБОТКИ СЕРТИФИКАТОВ", "header")
            self.log_message("=" * 60)
            
            try:
                for i, (script_id, script_info) in enumerate(self.scripts.items(), 1):
                    self.log_message(f"📋 ЭТАП {i}/4: {script_info['title']}", "header")
                    
                    success = self.run_script_process(script_info['name'], script_info['title'])
                    
                    if success:
                        successful_stages += 1
                        self.log_message(f"✅ Этап {i} завершен успешно", "success")
                    else:
                        self.log_message(f"❌ Этап {i} завершен с ошибкой", "error")
                        if i == 1:  # Если первый этап не удался
                            self.log_message("⚠️ Первый этап не удался. Остальные этапы могут быть неактуальны.", "warning")
                    
                    self.log_message("-" * 40)
                    time.sleep(1)
                
                total_time = time.time() - start_time
                
                self.log_message("🏆 ПОЛНАЯ ОБРАБОТКА ЗАВЕРШЕНА", "header")
                self.log_message(f"⏱️ Общее время: {total_time/60:.1f} минут", "info")
                self.log_message(f"✅ Успешных этапов: {successful_stages}/4", "success")
                
                if successful_stages == 4:
                    self.log_message("🎉 ВСЕ ЭТАПЫ ВЫПОЛНЕНЫ УСПЕШНО!", "success")
                    self.log_message("📁 Результаты находятся в папке 'сертификаты'", "info")
                    self.update_status("Полная обработка завершена", "#4CAF50")
                else:
                    self.log_message(f"⚠️ Некоторые этапы завершились с ошибками", "warning")
                    self.update_status("Обработка завершена с ошибками", "#FF9800")
                    
            except Exception as e:
                self.log_message(f"❌ Критическая ошибка полной обработки: {e}", "error")
                self.update_status("Критическая ошибка", "#F44336")
            finally:
                self.is_processing = False
                self.progress.stop()
                self.enable_buttons()
                self.current_process = None
        
        threading.Thread(target=run_thread, daemon=True).start()
    
    def stop_process(self):
        """Остановка текущего процесса"""
        if self.current_process and self.is_processing:
            try:
                self.current_process.terminate()
                self.log_message("⏹️ Процесс остановлен пользователем", "warning")
                self.update_status("Остановлено", "#FF9800")
            except Exception as e:
                self.log_message(f"❌ Ошибка остановки: {e}", "error")
            finally:
                self.is_processing = False
                self.progress.stop()
                self.enable_buttons()
                self.current_process = None
    
    def clear_logs(self):
        """Очистка логов"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("🗑️ Логи очищены", "info")
    
    def run(self):
        """Запуск приложения"""
        try:
            self.log_message("🎓 Система обработки сертификатов загружена", "header")
            self.log_message("📁 Базовая папка: " + str(self.base_dir), "info")
            self.log_message("✨ Готов к работе!", "success")
            
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            messagebox.showerror("Критическая ошибка", f"Ошибка запуска приложения: {e}")
    
    def on_closing(self):
        """Обработка закрытия приложения"""
        if self.is_processing:
            result = messagebox.askyesno(
                "Выход", 
                "Сейчас выполняется обработка.\n"
                "Остановить процесс и выйти?"
            )
            if result:
                self.stop_process()
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    """Главная функция"""
    try:
        app = CertificateProcessorGUI()
        app.run()
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()