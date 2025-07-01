import os
import re
import requests
import json
import time
from pathlib import Path
from datetime import datetime

class CompleteFIOFixer:
    """Полная версия исправителя ФИО с патчем - решает ВСЕ проблемы"""
    
    def __init__(self, base_path="сертификаты"):
        self.base_path = Path(base_path)
        self.yandex_speller_url = "https://speller.yandex.net/services/spellservice.json/checkText"
        
        # Кэш для API
        self.api_cache = {}
        
        # Расширенные словари имен
        self.male_names = {
            'александр', 'алексей', 'андрей', 'антон', 'артем', 'артём', 'владимир',
            'дмитрий', 'денис', 'евгений', 'иван', 'игорь', 'илья', 'константин',
            'максим', 'михаил', 'николай', 'олег', 'павел', 'петр', 'роман',
            'сергей', 'станислав', 'юрий', 'ринат', 'семен', 'семён', 'виктор'
        }
        
        self.female_names = {
            'александра', 'анастасия', 'анна', 'валентина', 'вера', 'виктория',
            'дарья', 'дина', 'екатерина', 'елена', 'ирина', 'кристина',
            'ксения', 'лилия', 'людмила', 'мария', 'марина', 'наталья',
            'ольга', 'светлана', 'татьяна', 'юлия', 'эльвира', 'диана',
            'вероника', 'инна', 'олеся', 'заира'
        }
        
        # Специальные исправления имен (приоритет)
        self.name_direct_fixes = {
            'олесе': 'олеся',
            'екатеринс': 'екатерина',
            'натальс': 'наталья',
            'ксении': 'ксения', 
            'марии': 'мария',
            'анастасии': 'анастасия',
            'юлии': 'юлия',
            'дарье': 'дарья',
            'сергею': 'сергей',
            'александру': 'александр',
            'дмитрию': 'дмитрий',
            'олегу': 'олег',
            'денису': 'денис',     # ПАТЧ: Защищаем от API порчи
            'ивану': 'иван',
            'артёму': 'артём',
            'антону': 'антон',
            'станиславу': 'станислав',
            'ринату': 'ринат',
            'семену': 'семен',
            'илье': 'илья',
        }
        
        # ПАТЧ: Амбивалентные имена (могут быть мужскими или женскими)
        self.ambiguous_names = {
            'александре': {
                'male_version': 'александр',
                'female_version': 'александра'
            }
        }
        
        # ПАТЧ: Определение пола по фамилии
        self.surname_gender_hints = {
            'репиной': 'female',
            'харькиной': 'female',
            'ивановой': 'female',
            'петровой': 'female',
            'сидоровой': 'female',
            'смирновой': 'female',
            'кузнецовой': 'female',
            'поповой': 'female',
            'васильевой': 'female',
            'козловой': 'female',
            'новиковой': 'female',
            'морозовой': 'female',
        }
        
        # OCR исправления
        self.ocr_fixes_by_position = {
            'names': {
                'екатеринс': 'екатерина',
                'натальс': 'наталья',
                'алсксандровне': 'александровне',
                'фсдоровне': 'федоровне',
                'с$': 'а',
                'л$': 'н',
                'п$': 'н',
                'ч$': 'н',
            },
            'patronymics': {
                'алсксандровне': 'александровне',
                'фсдоровне': 'федоровне',
                'халиловне': 'халиловне',
            }
        }
        
        # Правила падежа
        self.dative_rules = {
            'female_surnames': [
                ('иной', 'ина'), ('овой', 'ова'), ('евой', 'ева'), 
                ('ской', 'ская'), ('цкой', 'цкая'), ('ой', 'а'), ('ей', 'я'),
            ],
            'female_names': [
                ('ии', 'ия'), ('ье', 'ья'), ('ине', 'ина'), 
                ('ене', 'ена'), ('ане', 'ана'), ('е', 'а'),
            ],
            'female_patronymics': [
                ('овне', 'овна'), ('евне', 'евна'), ('ичне', 'ична'),
            ],
            'male_surnames': [
                ('ину', 'ин'), ('ову', 'ов'), ('еву', 'ев'), 
                ('скому', 'ский'), ('цкому', 'цкий'), ('ому', ''), ('ему', ''),
            ],
            'male_names': [
                ('ею', 'ей'), ('ию', 'ий'),
            ],
            'male_patronymics': [
                ('овичу', 'ович'), ('евичу', 'евич'), ('ичу', 'ич'),
            ]
        }
        
        # Статистика
        self.stats = {
            'total_files': 0, 'renamed_files': 0, 'api_calls': 0, 'api_fixes': 0,
            'direct_fixes': 0, 'ocr_fixes': 0, 'case_fixes': 0, 'ambiguous_fixes': 0, 'errors': 0
        }
        
        self.report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'renamed_files': [], 'errors': []
        }
    
    def check_internet_connection(self):
        """Проверяет интернет"""
        try:
            response = requests.get("https://www.google.com", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def detect_gender_improved(self, words):
        """Улучшенное определение пола с учетом фамилии"""
        if len(words) < 2:
            return 'unknown', {}
        
        # Сначала проверяем по фамилии
        surname = words[0].lower()
        if surname in self.surname_gender_hints:
            gender = self.surname_gender_hints[surname]
            return gender, {'surname_pos': 0, 'name_pos': 1, 'patronymic_pos': 2 if len(words) >= 3 else None}
        
        # Проверяем амбивалентные имена
        if len(words) >= 2:
            name = words[1].lower()
            if name in self.ambiguous_names:
                # Определяем по отчеству
                if len(words) >= 3:
                    patronymic = words[2].lower()
                    if patronymic.endswith(('овне', 'евне', 'ичне', 'овна', 'евна', 'ична')):
                        return 'female', {'surname_pos': 0, 'name_pos': 1, 'patronymic_pos': 2}
                    elif patronymic.endswith(('овичу', 'евичу', 'ичу', 'ович', 'евич', 'ич')):
                        return 'male', {'surname_pos': 0, 'name_pos': 1, 'patronymic_pos': 2}
                
                # Определяем по фамилии
                if surname.endswith(('ой', 'ей')):
                    return 'female', {'surname_pos': 0, 'name_pos': 1, 'patronymic_pos': 2 if len(words) >= 3 else None}
        
        # Стандартная логика
        name = words[1].lower()
        name_base = re.sub(r'(е|у|ю|ей|ем|ым|ой|ою|ий|ая|ые|их|ии|ье|ине|ене|ане)$', '', name)
        
        if name_base in self.male_names or name in self.male_names:
            gender = 'male'
        elif name_base in self.female_names or name in self.female_names:
            gender = 'female'
        else:
            # По отчеству или фамилии
            if len(words) >= 3:
                patronymic = words[2].lower()
                if patronymic.endswith(('овичу', 'евичу', 'ичу', 'ович', 'евич', 'ич')):
                    gender = 'male'
                elif patronymic.endswith(('овне', 'евне', 'ичне', 'овна', 'евна', 'ична')):
                    gender = 'female'
                else:
                    gender = 'unknown'
            else:
                gender = 'unknown'
        
        return gender, {'surname_pos': 0, 'name_pos': 1, 'patronymic_pos': 2 if len(words) >= 3 else None}
    
    def apply_direct_fixes(self, word, position):
        """Применяет прямые исправления (высший приоритет)"""
        word_lower = word.lower()
        
        if word_lower in self.name_direct_fixes:
            corrected = self.name_direct_fixes[word_lower]
            if word[0].isupper():
                corrected = corrected[0].upper() + corrected[1:]
            if corrected != word:
                self.stats['direct_fixes'] += 1
                return corrected, True
        
        return word, False
    
    def apply_ambiguous_name_fix(self, word, position, gender):
        """Исправляет амбивалентные имена"""
        if position != 1:  # Только для имен
            return word, False
            
        word_lower = word.lower()
        
        if word_lower in self.ambiguous_names:
            ambiguous = self.ambiguous_names[word_lower]
            
            if gender == 'female':
                corrected = ambiguous['female_version']
            elif gender == 'male':
                corrected = ambiguous['male_version']
            else:
                return word, False
            
            # Восстанавливаем регистр
            if word[0].isupper():
                corrected = corrected[0].upper() + corrected[1:]
            
            if corrected != word:
                self.stats['ambiguous_fixes'] += 1
                return corrected, True
        
        return word, False
    
    def apply_ocr_fixes(self, word, position):
        """Применяет OCR исправления"""
        if position == 1:  # имена
            fixes = self.ocr_fixes_by_position['names']
        elif position == 2:  # отчества
            fixes = self.ocr_fixes_by_position['patronymics']
        else:
            return word, False
        
        word_lower = word.lower()
        
        # Прямые замены
        for error, correction in fixes.items():
            if not error.endswith('$'):  # Не регекс
                if word_lower == error:
                    corrected = correction
                    if word[0].isupper():
                        corrected = corrected[0].upper() + corrected[1:]
                    if corrected != word:
                        self.stats['ocr_fixes'] += 1
                        return corrected, True
        
        # Регекс замены
        for pattern, replacement in fixes.items():
            if pattern.endswith('$'):  # Это регекс для конца слова
                regex_pattern = pattern.replace('$', '') + '$'
                if re.search(regex_pattern, word_lower):
                    corrected = re.sub(regex_pattern, replacement, word_lower)
                    if word[0].isupper():
                        corrected = corrected[0].upper() + corrected[1:]
                    if corrected != word:
                        self.stats['ocr_fixes'] += 1
                        return corrected, True
        
        return word, False
    
    def correct_with_api_extra_safe(self, text, position):
        """Максимально безопасное API исправление"""
        if not text or len(text) < 3:
            return text, False
        
        # НЕ исправляем фамилии
        if position == 0:
            return text, False
        
        # Защищаем конкретные проблемные слова
        protected_words = ['денису', 'александре', 'дмитрию', 'сергею', 'олегу']
        if text.lower() in protected_words:
            return text, False
        
        # НЕ исправляем отчества с проблемными окончаниями
        if position == 2 and text.lower().endswith(('халиловне', 'овне', 'евне', 'ичне')):
            return text, False
        
        if text in self.api_cache:
            cached_result = self.api_cache[text]
            return cached_result, cached_result != text
        
        try:
            params = {'text': text, 'lang': 'ru', 'options': 518}
            response = requests.get(self.yandex_speller_url, params=params, timeout=10)
            self.stats['api_calls'] += 1
            
            if response.status_code == 200:
                corrections = response.json()
                
                if corrections and corrections[0].get('s'):
                    suggested = corrections[0]['s'][0]
                    
                    if self.is_very_safe_correction(text, suggested, position):
                        self.api_cache[text] = suggested
                        if suggested != text:
                            self.stats['api_fixes'] += 1
                        return suggested, suggested != text
                
            self.api_cache[text] = text
            return text, False
            
        except Exception as e:
            self.report['errors'].append(f"API ошибка для '{text}': {str(e)}")
            return text, False
    
    def is_very_safe_correction(self, original, suggested, position):
        """Очень консервативная проверка API исправлений"""
        # Не принимаем большие изменения
        if abs(len(original) - len(suggested)) > 1:
            return False
        
        # Не принимаем изменения регистра в начале
        if original[0].isupper() and suggested[0].islower():
            return False
        
        # Не принимаем исправления, которые добавляют пробелы
        if ' ' in suggested and ' ' not in original:
            return False
        
        # Для имен - дополнительная проверка
        if position == 1:
            suggested_base = re.sub(r'[ауеюяий]+$', '', suggested.lower())
            if (suggested_base not in self.male_names and 
                suggested_base not in self.female_names):
                return False
        
        return True
    
    def apply_case_rules(self, word, position, gender):
        """Применяет правила склонения"""
        word_lower = word.lower()
        
        # Определяем тип слова и соответствующие правила
        if position == 0:  # фамилия
            if gender == 'female':
                rules = self.dative_rules['female_surnames']
            else:
                rules = self.dative_rules['male_surnames']
        elif position == 1:  # имя
            if gender == 'female':
                rules = self.dative_rules['female_names']
            else:
                rules = self.dative_rules['male_names']
        elif position == 2:  # отчество
            if gender == 'female':
                rules = self.dative_rules['female_patronymics']
            else:
                rules = self.dative_rules['male_patronymics']
        else:
            return word, False
        
        # Применяем правила
        for dative_ending, nominative_ending in rules:
            if word_lower.endswith(dative_ending.lower()):
                root = word[:-len(dative_ending)] if dative_ending else word
                new_word = root + nominative_ending
                
                # Сохраняем регистр
                if word[0].isupper():
                    new_word = new_word[0].upper() + new_word[1:].lower()
                
                if new_word != word:
                    self.stats['case_fixes'] += 1
                    return new_word, True
                break
        
        return word, False
    
    def correct_word_complete(self, word, position, gender, use_api=True):
        """Полная функция исправления слова"""
        if len(word) < 2:
            return word, False
        
        original_word = word
        was_changed = False
        
        # Шаг 1: Прямые исправления (наивысший приоритет)
        word, changed = self.apply_direct_fixes(word, position)
        if changed:
            was_changed = True
        
        # Шаг 2: Амбивалентные имена
        word, changed = self.apply_ambiguous_name_fix(word, position, gender)
        if changed:
            was_changed = True
        
        # Шаг 3: OCR исправления
        word, changed = self.apply_ocr_fixes(word, position)
        if changed:
            was_changed = True
        
        # Шаг 4: API исправления (максимально осторожно)
        if use_api and position > 0:
            word, changed = self.correct_with_api_extra_safe(word, position)
            if changed:
                was_changed = True
            time.sleep(0.1)
        
        # Шаг 5: Правила склонения
        word, changed = self.apply_case_rules(word, position, gender)
        if changed:
            was_changed = True
        
        return word, was_changed
    
    def correct_fio_complete(self, filename, use_api=True):
        """Полная функция исправления ФИО"""
        # Извлекаем имя файла
        name_without_ext = Path(filename).stem
        name_without_ext = re.sub(r'_\d+$', '', name_without_ext)
        
        # Очистка
        clean_name = re.sub(r'[^\w\sа-яёА-ЯЁ]', ' ', name_without_ext)
        clean_name = re.sub(r'\s+', ' ', clean_name.strip())
        
        if not clean_name:
            return filename, False
        
        words = clean_name.split()
        if len(words) < 2:
            return filename, False
        
        # Улучшенное определение пола
        gender, positions = self.detect_gender_improved(words)
        
        corrected_words = []
        any_changes = False
        
        for i, word in enumerate(words):
            if len(word) < 2:
                continue
            
            # Исправляем слово с учетом всех патчей
            corrected_word, was_changed = self.correct_word_complete(word, i, gender, use_api)
            
            if was_changed:
                any_changes = True
            
            corrected_words.append(corrected_word)
        
        if corrected_words and any_changes:
            result = ' '.join(corrected_words) + Path(filename).suffix
            return result, True
        
        return filename, False
    
    def sanitize_filename(self, filename):
        """Очищает имя файла"""
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
        cleaned = re.sub(r'\s+', ' ', cleaned.strip())
        
        if len(cleaned) > 100:
            name_part = Path(cleaned).stem[:90]
            ext_part = Path(cleaned).suffix
            cleaned = name_part + ext_part
        
        return cleaned
    
    def process_directory(self, directory_path, use_api=True):
        """Обрабатывает папку"""
        directory = Path(directory_path)
        
        if not directory.exists():
            return 0, 0
        
        pdf_files = list(directory.glob("*.pdf"))
        renamed_count = 0
        
        print(f"📁 Папка: {directory.name}")
        print(f"   Найдено PDF файлов: {len(pdf_files)}")
        
        for pdf_file in pdf_files:
            self.stats['total_files'] += 1
            
            try:
                original_name = pdf_file.name
                corrected_name, was_changed = self.correct_fio_complete(original_name, use_api)
                
                if was_changed:
                    safe_name = self.sanitize_filename(corrected_name)
                    new_path = pdf_file.parent / safe_name
                    
                    # Избегаем конфликтов
                    counter = 1
                    while new_path.exists() and new_path != pdf_file:
                        name_part = Path(safe_name).stem
                        ext_part = Path(safe_name).suffix
                        safe_name = f"{name_part}_{counter}{ext_part}"
                        new_path = pdf_file.parent / safe_name
                        counter += 1
                    
                    if new_path != pdf_file:
                        pdf_file.rename(new_path)
                        renamed_count += 1
                        self.stats['renamed_files'] += 1
                        
                        print(f"   ✅ {original_name} -> {safe_name}")
                        
                        self.report['renamed_files'].append({
                            'directory': str(directory.relative_to(self.base_path)),
                            'original': original_name,
                            'corrected': safe_name,
                            'full_path': str(new_path)
                        })
                else:
                    print(f"   ⚪ {original_name} (без изменений)")
                    
            except Exception as e:
                self.stats['errors'] += 1
                error_msg = f"Ошибка с файлом {pdf_file.name}: {str(e)}"
                print(f"   ❌ {error_msg}")
                self.report['errors'].append(error_msg)
        
        return len(pdf_files), renamed_count
    
    def run_complete_processing(self, use_api=True):
        """Запуск полной обработки с патчем"""
        if not self.base_path.exists():
            print(f"❌ Папка '{self.base_path}' не найдена!")
            return
        
        print(f"📂 Базовая папка: {self.base_path}")
        print(f"👥 Определение пола по фамилии: ВКЛ")
        print(f"🌐 API: {'Включено' if use_api else 'Отключено'}")
        
        if use_api:
            if self.check_internet_connection():
                print("✅ Интернет: OK")
            else:
                print("❌ Интернет недоступен, API отключено")
                use_api = False
        
        print("="*60)
        
        start_time = time.time()
        
        # Находим папки
        event_dirs = [d for d in self.base_path.iterdir() 
                     if d.is_dir() and d.name != "Неопознанные"]
        
        print(f"📋 Найдено папок с мероприятиями: {len(event_dirs)}")
        print()
        
        total_files = 0
        total_renamed = 0
        
        for i, event_dir in enumerate(event_dirs, 1):
            print(f"🎯 [{i}/{len(event_dirs)}] Обработка...")
            files_count, renamed_count = self.process_directory(event_dir, use_api)
            total_files += files_count
            total_renamed += renamed_count
            print(f"   📊 Результат: {renamed_count} из {files_count} файлов переименованы")
            print()
            
            if use_api and i < len(event_dirs):
                time.sleep(0.5)
        
        # Обрабатываем "Неопознанные"
        unknown_dir = self.base_path / "Неопознанные"
        if unknown_dir.exists():
            print(f"🔍 Обработка папки 'Неопознанные'")
            files_count, renamed_count = self.process_directory(unknown_dir, use_api)
            total_files += files_count
            total_renamed += renamed_count
            print(f"   📊 Результат: {renamed_count} из {files_count} файлов переименованы")
        
        # Итоги
        elapsed_time = time.time() - start_time
        
        print("="*60)
        print(f"🏆 ПОЛНАЯ ОБРАБОТКА С ПАТЧЕМ ЗАВЕРШЕНА!")
        print(f"⏱️  Время: {elapsed_time/60:.1f} минут")
        print(f"📄 Всего файлов: {total_files}")
        print(f"✅ Переименовано: {total_renamed}")
        print(f"🌐 API запросов: {self.stats['api_calls']}")
        print(f"🔧 API исправлений: {self.stats['api_fixes']}")
        print(f"🎯 Прямых исправлений: {self.stats['direct_fixes']}")
        print(f"🧩 Амбивалентных исправлений: {self.stats['ambiguous_fixes']}")
        print(f"🔤 OCR исправлений: {self.stats['ocr_fixes']}")
        print(f"📝 Исправлений падежа: {self.stats['case_fixes']}")
        
        if self.stats['errors'] > 0:
            print(f"❌ Ошибок: {self.stats['errors']}")
        
        # Сохраняем отчет
        self.save_report()
        
        return total_renamed, total_files
    
    def save_report(self):
        """Сохраняет отчет"""
        self.report['stats'] = self.stats
        
        report_file = self.base_path / f"complete_fio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.report, f, ensure_ascii=False, indent=2)
            
            print(f"📊 Отчет сохранен: {report_file.name}")
                
        except Exception as e:
            print(f"⚠️  Ошибка сохранения отчета: {e}")

def main():
    
    fixer = CompleteFIOFixer("сертификаты")
    
    use_api = True

    print()
    fixer.run_complete_processing(use_api=use_api)

if __name__ == "__main__":
    main()