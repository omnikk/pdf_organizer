import os
import re
import shutil
import pandas as pd
from pathlib import Path
import easyocr
from pdf2image import convert_from_path
import cv2
import numpy as np
from datetime import datetime
from collections import Counter
import warnings
import time

# Отключаем предупреждения для чистого вывода
warnings.filterwarnings("ignore")

class CertificateProcessorBalanced:
    def __init__(self):
        # Проверяем доступность CUDA
        import torch
        if torch.cuda.is_available():
            print(f"[START] Используется GPU: {torch.cuda.get_device_name(0)}")
            self.reader = easyocr.Reader(['ru'], gpu=True, verbose=False)
        else:
            print("[CPU] Используется CPU (GPU недоступен)")
            self.reader = easyocr.Reader(['ru'], gpu=False, verbose=False)
            
        self.base_dir = Path.cwd()
        self.input_dir = self.base_dir / "input"
        self.certificates_dir = self.base_dir / "сертификаты"
        self.debug_dir = self.base_dir / "debug"
        self.unknown_dir = self.certificates_dir / "Неопознанные"
        
        # Создаем необходимые папки
        self.create_directories()
        
        # Список для CSV
        self.csv_data = []
        
        # Статистика времени
        self.timing_stats = []
        
    def create_directories(self):
        """Создает необходимые папки если их нет"""
        for directory in [self.certificates_dir, self.debug_dir, self.unknown_dir]:
            directory.mkdir(exist_ok=True)
    
    def preprocess_image_enhanced(self, image):
        """Улучшенная предобработка (лучший вариант)"""
        # Конвертируем в оттенки серого
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Увеличиваем размер изображения для лучшего распознавания
        height, width = gray.shape
        gray = cv2.resize(gray, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
        
        # Убираем шум
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Увеличиваем контрастность
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # Бинаризация с адаптивным порогом
        binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)
        
        return binary
    
    def preprocess_image_simple(self, image):
        """Простая предобработка (запасной вариант)"""
        # Конвертируем в оттенки серого
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Простое увеличение контрастности
        enhanced = cv2.convertScaleAbs(gray, alpha=1.5, beta=30)
        
        # Гауссово размытие для сглаживания
        blurred = cv2.GaussianBlur(enhanced, (1, 1), 0)
        
        return blurred
    
    def extract_text_from_pdf_balanced(self, pdf_path):
        """Сбалансированное извлечение текста (2-3 попытки)"""
        start_time = time.time()
        
        try:
            # Конвертируем PDF в изображения с хорошим качеством
            images = convert_from_path(pdf_path, dpi=300)
            pdf_time = time.time() - start_time
            
            all_text = ""
            ocr_start = time.time()
            
            for image in images:
                # Конвертируем PIL в opencv формат
                opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Пробуем 3 варианта обработки (вместо 6)
                attempts = [
                    ("enhanced", self.preprocess_image_enhanced(opencv_image)),
                    ("simple", self.preprocess_image_simple(opencv_image)),
                    ("original", opencv_image)
                ]
                
                page_texts = []
                successful_attempts = []
                
                for attempt_name, processed_image in attempts:
                    try:
                        # Только один OCR вызов для каждого варианта (не 2)
                        result = self.reader.readtext(processed_image, detail=0, paragraph=False)
                        text = " ".join(result)
                        
                        if text.strip():  # Проверяем, что текст не пустой
                            page_texts.append(text)
                            successful_attempts.append(attempt_name)
                        
                    except Exception as e:
                        continue
                
                # Выбираем самый длинный результат (обычно лучший)
                if page_texts:
                    best_text = max(page_texts, key=len)
                    best_idx = page_texts.index(best_text)
                    best_method = successful_attempts[best_idx]
                    
                    all_text += best_text + " "
                    
                    # Логируем какой метод сработал лучше
                    if len(page_texts) > 1:
                        print(f"    [FIX] Лучший метод: {best_method} ({len(best_text)} символов)")
            
            ocr_time = time.time() - ocr_start
            total_time = time.time() - start_time
            
            # Сохраняем статистику
            self.timing_stats.append({
                'file': pdf_path.name,
                'pdf_convert': pdf_time,
                'ocr_time': ocr_time,
                'total_time': total_time,
                'text_length': len(all_text)
            })
            
            return all_text
            
        except Exception as e:
            print(f"[ERROR] Ошибка при обработке {pdf_path}: {e}")
            return ""
    
    def extract_fio(self, text):
        """Извлекает ФИО из текста"""
        try:
            # Очищаем текст от лишних символов
            cleaned_text = re.sub(r'[^\w\sа-яёА-ЯЁ]', ' ', text)
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
            
            # Несколько вариантов поиска ФИО
            patterns = [
                r"Настоящее удостоверение выдано\s+(.*?)\s+в\s+том",
                r"удостоверение выдано\s+(.*?)\s+в\s+том",
                r"выдано\s+(.*?)\s+в\s+том\s+что",
                r"выдано\s+([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)",
            ]
            
            for pattern in patterns:
                match = re.search(pattern, cleaned_text, re.IGNORECASE | re.DOTALL)
                if match:
                    fio_raw = match.group(1).strip()
                    # Проверяем, что это похоже на ФИО (3 слова, начинающиеся с заглавной)
                    if self.validate_fio(fio_raw):
                        fio_clean = self.normalize_fio(fio_raw)
                        return fio_clean
            
            # Дополнительный поиск по паттернам русских имен
            fio_pattern = r'([А-ЯЁ][а-яё]+(?:ой|ей|ому|ему|ной|ному|ской|ский)\s+[А-ЯЁ][а-яё]+(?:е|у|ь)?\s+[А-ЯЁ][а-яё]+(?:ичу|овичу|евичу|ичем|овичем|евичем|овне|евне|ичне))'
            match = re.search(fio_pattern, text)
            if match:
                fio_raw = match.group(1).strip()
                if self.validate_fio(fio_raw):
                    return self.normalize_fio(fio_raw)
            
            return None
        except Exception as e:
            print(f"Ошибка при извлечении ФИО: {e}")
            return None
    
    def validate_fio(self, fio):
        """Проверяет, похож ли текст на ФИО"""
        words = fio.split()
        if len(words) < 2 or len(words) > 4:
            return False
        
        # Проверяем, что все слова начинаются с заглавной буквы
        for word in words:
            if not word or not word[0].isupper() or len(word) < 2:
                return False
        
        return True
    
    def normalize_fio(self, fio_raw):
        """Очищает ФИО (без изменения падежа)"""
        fio = fio_raw.strip()
        
        # Очищаем от лишних пробелов и приводим к правильному регистру
        words = fio.split()
        normalized_words = []
        
        for word in words:
            if word:
                # Первая буква заглавная, остальные строчные
                normalized_word = word[0].upper() + word[1:].lower()
                normalized_words.append(normalized_word)
        
        result = ' '.join(normalized_words)
        return result
    
    def extract_program_name(self, text):
        """Извлекает название программы"""
        try:
            # Очищаем текст от мусорных символов
            cleaned_text = re.sub(r'[^\w\sа-яёА-ЯЁ\-\(\)\.\,\:\"«»]', ' ', text)
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
            
            # Несколько вариантов поиска названия программы
            patterns = [
                r'по программе\s*["\u201C«]?\s*(.*?)\s*["\u201D»]?\s*в\s*объеме',
                r'по программе\s*["\u201C«]?\s*(.*?)\s*["\u201D»]?\s*\d+\s*час',
                r'по программе\s*["\u201C«]?\s*(.*?)\s*["\u201D»]?\s*№',
                r'программе\s*["\u201C«]?\s*(.*?)\s*["\u201D»]?\s*в\s*объ[её]ме',
                r'программе\s*["\u201C«]?\s*(.*?)\s*["\u201D»]?\s*\d+\s*час',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, cleaned_text, re.IGNORECASE | re.DOTALL)
                if match:
                    program_name = match.group(1).strip()
                    
                    # Очищаем название от мусора
                    program_name = self.clean_program_name(program_name)
                    
                    # Проверяем минимальную длину и разумность
                    if len(program_name) > 10 and self.validate_program_name(program_name):
                        return program_name
            
            # Поиск стандартных названий программ без учета "по программе"
            standard_programs = [
                r'(Государственн[ыые]+\s+и\s+муниципальн[ыые]+\s+закупки.*?(?:теория\s+и\s+практика|практика))',
                r'([Оо0]\s*контрактной\s+системе\s+в\s+сфере\s+закупок)',
                r'(44.*?ФЗ.*?закуп)',
                r'(контрактн[оая]+\s+систем[ае]\s+в\s+сфере\s+закупок)',
            ]
            
            for pattern in standard_programs:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    program_name = self.clean_program_name(match.group(1))
                    if len(program_name) > 10:
                        return program_name
            
            # Дополнительный поиск для искаженного текста
            fallback_patterns = [
                r'(Государствен[а-яшые]*\s+и\s+муниципальн[а-яшые]*\s+закупки[^"]*(?:теория|практика)?)',
                r'([Оо0]\s*контрактн[а-я]*\s+систем[а-я]*\s+в\s+сфере\s+закупок[а-я]*)',
                r'(Государств[а-яшые]*\s+[ия]*\s*муници[а-яшые]*\s+закуп[а-яки]*)',
                r'(44[^"]*ФЗ[^"]*закуп[а-яки]*)',
            ]
            
            for pattern in fallback_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    program_name = self.clean_program_name(match.group(1))
                    if len(program_name) > 15:
                        return program_name
            
            return None
        except Exception as e:
            print(f"Ошибка при извлечении названия программы: {e}")
            return None
    
    def clean_program_name(self, name):
        """Очищает название программы"""
        if not name:
            return ""
        
        # Убираем кавычки и лишние символы
        name = re.sub(r'["\u201C\u201D«»()"]', '', name)
        name = re.sub(r'\s+', ' ', name)
        name = name.strip()
        
        # Убираем мусорные символы в конце и начале
        name = re.sub(r'^[^\w]*', '', name)
        name = re.sub(r'[\*\#\{\}\[\]\$\%\@\!\+\=\<\>]+.*$', '', name)
        
        # Убираем повторяющиеся символы (более 3 подряд)
        name = re.sub(r'(.)\1{3,}', r'\1', name)
        
        # Убираем фразы "в объёме", "в объеме" и цифры после них
        name = re.sub(r'\s*[вВ]\s*объ[её]ме.*$', '', name)
        name = re.sub(r'\s*[вВ]\s*обь[её]ме.*$', '', name)
        name = re.sub(r'\s*объ[её]мс.*$', '', name)
        name = re.sub(r'\s*объ[её]не.*$', '', name)
        name = re.sub(r'\s*оь[её]ме.*$', '', name)
        name = re.sub(r'\s*\d+\s*час.*$', '', name)
        name = re.sub(r'\s*\d+\s*₽.*$', '', name)
        
        # Заменяем искаженные символы
        replacements = [
            ('0', 'О'),
            ('Государствен[а-яшы]*', 'Государственные'),
            ('Государств[а-яшы]*', 'Государственные'),
            ('муниципальн[а-яшы]*', 'муниципальные'),
            ('муници[а-яшы]*', 'муниципальные'),
            ('контрактн[а-я]*', 'контрактной'),
            ('коптрактн[а-я]*', 'контрактной'),
            ('систем[а-я]*', 'системе'),
            ('закупок[ъэ]', 'закупок'),
            ('закуп[а-яки]*', 'закупки'),
            ('44[^"]*ФЗ', '44-ФЗ'),
        ]
        
        for pattern, replacement in replacements:
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)
        
        # Нормализуем пробелы
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip()
    
    def validate_program_name(self, name):
        """Проверяет разумность названия программы"""
        letters = len(re.findall(r'[а-яёА-ЯЁ]', name))
        total = len(name)
        
        if total == 0:
            return False
        
        return (letters / total) > 0.7
    
    def extract_certificate_number(self, text):
        """Извлекает номер сертификата"""
        try:
            patterns = [
                r'(\d{2}\s*[А-ЯЁ]{2,5}\d?\s*\d{6})',
                r'(\d{2}\s+[А-ЯЁ]+\s*\d+)',
                r'([А-ЯЁ]{2,5}\s*\d{6,8})',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    return matches[0].strip()
                
            return None
        except Exception as e:
            return None
    
    def extract_date(self, text):
        """Извлекает дату"""
        try:
            pattern = r'(\d{1,2}\.\d{1,2}\.\d{4})'
            matches = re.findall(pattern, text)
            
            if matches:
                return matches[-1]
            
            return None
        except Exception as e:
            return None
    
    def extract_hours(self, text):
        """Извлекает количество часов"""
        try:
            patterns = [
                r'в\s*объ[её]ме\s*(\d+)\s*час',
                r'Всего\s*(\d+)',
                r'(\d+)\s*час[аов]?(?:\s|$)',
                r'объёмс\s*(\d+)',
                r'объёне\s*(\d+)',
            ]
            
            found_hours = []
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    hours = int(match)
                    if 8 <= hours <= 1000:
                        found_hours.append(hours)
            
            if found_hours:
                hour_counts = Counter(found_hours)
                most_common_hours = hour_counts.most_common(1)[0][0]
                return str(most_common_hours)
            
            return None
        except Exception as e:
            return None
    
    def sanitize_filename(self, filename):
        """Очищает имя файла от недопустимых символов"""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', ' ', filename)
        if len(filename) > 100:
            filename = filename[:100]
        return filename.strip()
    
    def process_single_pdf(self, pdf_path, file_number, total_files):
        """Обрабатывает один PDF файл"""
        print(f"\n[PDF] Файл {file_number}/{total_files}: {pdf_path.name}")
        
        file_start_time = time.time()
        
        # Извлекаем текст сбалансированным методом
        text = self.extract_text_from_pdf_balanced(pdf_path)
        
        if not text:
            print(f"[ERROR] Не удалось извлечь текст")
            return False
        
        # Создаем файл отладки с распознанным текстом
        debug_text_file = self.debug_dir / f"{pdf_path.stem}_ocr_text.txt"
        with open(debug_text_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # Извлекаем данные
        fio = self.extract_fio(text)
        program_name = self.extract_program_name(text)
        cert_number = self.extract_certificate_number(text)
        cert_date = self.extract_date(text)
        hours = self.extract_hours(text)
        
        # Показываем время обработки файла
        file_time = time.time() - file_start_time
        print(f"[TIME]  Время: {file_time:.1f}с | Текст: {len(text)} символов")
        
        # Краткий вывод результата
        print(f"[USER] ФИО: {fio[:30] + '...' if fio and len(fio) > 30 else fio or 'НЕ НАЙДЕНО'}")
        print(f"[CERT] Программа: {program_name[:40] + '...' if program_name and len(program_name) > 40 else program_name or 'НЕ НАЙДЕНО'}")
        
        # Проверяем обязательные поля
        if not fio or not program_name:
            print(f"[ERROR] Обработка неудачна")
            shutil.copy2(pdf_path, self.unknown_dir / pdf_path.name)
            
            self.csv_data.append({
                'ФИО': fio or 'НЕ НАЙДЕНО',
                'Название': program_name or 'НЕ НАЙДЕНО',
                'Номер': cert_number or '',
                'Дата': cert_date or '',
                'Часы': hours or '',
                'Путь к файлу': str(self.unknown_dir / pdf_path.name)
            })
            return False
        
        # Создаем папку для программы и копируем файл
        safe_program_name = self.sanitize_filename(program_name)
        program_dir = self.certificates_dir / safe_program_name
        program_dir.mkdir(exist_ok=True)
        
        safe_fio = self.sanitize_filename(fio)
        new_filename = f"{safe_fio}.pdf"
        new_path = program_dir / new_filename
        
        counter = 1
        while new_path.exists():
            new_filename = f"{safe_fio}_{counter}.pdf"
            new_path = program_dir / new_filename
            counter += 1
        
        shutil.copy2(pdf_path, new_path)
        
        self.csv_data.append({
            'ФИО': fio,
            'Название': program_name,
            'Номер': cert_number or '',
            'Дата': cert_date or '',
            'Часы': hours or '',
            'Путь к файлу': str(new_path)
        })
        
        print(f"[OK] Успешно обработан")
        return True
    
    def show_timing_stats(self):
        """Показывает статистику времени"""
        if not self.timing_stats:
            return
            
        df = pd.DataFrame(self.timing_stats)
        
        avg_pdf = df['pdf_convert'].mean()
        avg_ocr = df['ocr_time'].mean()
        avg_total = df['total_time'].mean()
        avg_text_len = df['text_length'].mean()
        
        print(f"\n[TIME]  СТАТИСТИКА ВРЕМЕНИ:")
        print(f"   PDF конвертация: {avg_pdf:.1f} сек/файл")
        print(f"   OCR обработка: {avg_ocr:.1f} сек/файл") 
        print(f"   Общее время: {avg_total:.1f} сек/файл")
        print(f"   Средняя длина текста: {avg_text_len:.0f} символов")
        
        # Найти самый медленный и быстрый файлы
        slowest = df.loc[df['total_time'].idxmax()]
        fastest = df.loc[df['total_time'].idxmin()]
        print(f"   Самый медленный: {slowest['file']} ({slowest['total_time']:.1f} сек)")
        print(f"   Самый быстрый: {fastest['file']} ({fastest['total_time']:.1f} сек)")
    
    def process_all_pdfs(self):
        """Обрабатывает все PDF файлы в папке input"""
        if not self.input_dir.exists():
            print(f"[ERROR] Папка {self.input_dir} не найдена!")
            return
        
        pdf_files = list(self.input_dir.glob("*.pdf"))
        if not pdf_files:
            print("[ERROR] PDF файлы не найдены в папке input!")
            return
        
        print(f"[TARGET] Найдено {len(pdf_files)} PDF файлов")
        print("="*60)
        
        start_time = time.time()
        successful = 0
        
        for i, pdf_file in enumerate(pdf_files, 1):
            if self.process_single_pdf(pdf_file, i, len(pdf_files)):
                successful += 1
            
            # Показываем прогресс каждые 10 файлов
            if i % 10 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / i
                estimated_total = avg_time * len(pdf_files)
                remaining = estimated_total - elapsed
                
                print(f"\n[STATS] ПРОГРЕСС: {i}/{len(pdf_files)} файлов")
                print(f"   [OK] Успешно: {successful}/{i} ({successful/i*100:.1f}%)")
                print(f"   [TIME]  Прошло: {elapsed/60:.1f} мин")
                print(f"   Осталось: {remaining/60:.1f} мин")
                print(f"   [SPEED] Скорость: {avg_time:.1f} сек/файл")
        
        total_time = time.time() - start_time
        
        print(f"\n[SUCCESS] ОБРАБОТКА ЗАВЕРШЕНА!")
        print(f"[OK] Успешно обработано: {successful} из {len(pdf_files)} файлов ({successful/len(pdf_files)*100:.1f}%)")
        print(f"[TIME]  Общее время: {total_time/60:.1f} минут")
        print(f"[SPEED] Средняя скорость: {total_time/len(pdf_files):.1f} сек/файл")
        
        if successful < len(pdf_files):
            print(f"[ERROR] Неудачных файлов: {len(pdf_files) - successful}")
            print(f"[FOLDER] Проблемные файлы находятся в папке: Неопознанные")
        
        # Показываем детальную статистику времени
        self.show_timing_stats()
        
        # Сохраняем CSV
        self.save_csv()
    
    def save_csv(self):
        """Сохраняет данные в CSV файл"""
        if not self.csv_data:
            print("[WARNING]  Нет данных для сохранения в CSV")
            return
        
        df = pd.DataFrame(self.csv_data)
        csv_path = self.debug_dir / "table.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"[SAVE] Данные сохранены в {csv_path}")

def main():
    
    processor = CertificateProcessorBalanced()
    processor.process_all_pdfs()

if __name__ == "__main__":
    main()