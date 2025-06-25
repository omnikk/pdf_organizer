#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Интерактивный скрипт для объединения похожих папок с программами.
Позволяет пользователю выбирать название для объединенных папок.
"""

import os
import re
import shutil
from pathlib import Path
from difflib import SequenceMatcher

class FolderMerger:
    def __init__(self):
        self.base_dir = Path.cwd()
        self.certificates_dir = self.base_dir / "сертификаты"
        
    def get_similarity(self, a, b):
        """Вычисляет сходство между двумя строками (0-1)"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def extract_keywords(self, folder_name):
        """Извлекает ключевые слова из названия папки"""
        # Приводим к нижнему регистру и разбиваем на слова
        words = re.findall(r'\b\w+\b', folder_name.lower())
        
        # Ключевые слова для группировки
        keywords = set()
        
        if any(word in words for word in ['контрактной', 'контрактная', 'коптрактной']):
            keywords.add('контрактная_система')
        
        if any(word in words for word in ['государственные', 'государствен', 'государств']):
            keywords.add('государственные_закупки')
        
        if any(word in words for word in ['муниципальные', 'муниципальн', 'муници']):
            keywords.add('муниципальные_закупки')
        
        if any(word in words for word in ['44', 'фз', '44-фз']):
            keywords.add('44_фз')
        
        if any(word in words for word in ['теория', 'практика']):
            keywords.add('теория_практика')
        
        return keywords
    
    def group_similar_folders(self, folders):
        """Группирует похожие папки"""
        groups = []
        processed = set()
        
        for i, folder1 in enumerate(folders):
            if i in processed:
                continue
                
            # Создаем новую группу
            current_group = [folder1]
            processed.add(i)
            
            keywords1 = self.extract_keywords(folder1.name)
            
            # Ищем похожие папки
            for j, folder2 in enumerate(folders):
                if j in processed or i == j:
                    continue
                
                keywords2 = self.extract_keywords(folder2.name)
                
                # Проверяем сходство по ключевым словам
                if keywords1 and keywords2 and len(keywords1 & keywords2) >= 1:
                    current_group.append(folder2)
                    processed.add(j)
                    continue
                
                # Проверяем текстовое сходство
                similarity = self.get_similarity(folder1.name, folder2.name)
                if similarity > 0.6:  # 60% сходства
                    current_group.append(folder2)
                    processed.add(j)
            
            groups.append(current_group)
        
        return groups
    
    def suggest_group_names(self, group):
        """Предлагает варианты названий для группы папок"""
        # Анализируем все названия в группе
        all_keywords = set()
        for folder in group:
            keywords = self.extract_keywords(folder.name)
            all_keywords.update(keywords)
        
        suggestions = []
        
        # Предлагаем стандартные названия на основе ключевых слов
        if 'государственные_закупки' in all_keywords and 'муниципальные_закупки' in all_keywords:
            if '44_фз' in all_keywords:
                if 'теория_практика' in all_keywords:
                    suggestions.append("Государственные и муниципальные закупки (44-ФЗ) - теория и практика")
                else:
                    suggestions.append("Государственные и муниципальные закупки (44-ФЗ)")
            else:
                suggestions.append("Государственные и муниципальные закупки")
        
        elif 'контрактная_система' in all_keywords:
            suggestions.append("О контрактной системе в сфере закупок")
            suggestions.append("Контрактная система в сфере закупок")
        
        # Добавляем самое длинное название из группы как вариант
        longest_name = max(group, key=lambda f: len(f.name)).name
        if longest_name not in suggestions:
            suggestions.append(longest_name)
        
        # Добавляем самое короткое название
        shortest_name = min(group, key=lambda f: len(f.name)).name
        if shortest_name not in suggestions and len(shortest_name) > 10:
            suggestions.append(shortest_name)
        
        return suggestions
    
    def show_group_info(self, group, group_number):
        """Показывает информацию о группе папок"""
        print(f"\n📁 ГРУППА {group_number}:")
        print("=" * 50)
        
        total_files = 0
        for i, folder in enumerate(group, 1):
            file_count = len(list(folder.glob("*.pdf")))
            total_files += file_count
            print(f"  {i}. {folder.name} ({file_count} файлов)")
        
        print(f"\n📊 Всего файлов в группе: {total_files}")
        print(f"📂 Количество папок: {len(group)}")
        
        return total_files
    
    def choose_group_name(self, group, group_number):
        """Позволяет пользователю выбрать название для группы"""
        suggestions = self.suggest_group_names(group)
        
        print(f"\n💡 Предлагаемые названия:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
        
        print(f"  {len(suggestions) + 1}. Ввести свое название")
        print(f"  {len(suggestions) + 2}. Не объединять эту группу")
        
        while True:
            try:
                choice = input(f"\nВыберите название для группы {group_number} (1-{len(suggestions) + 2}): ").strip()
                
                if choice == str(len(suggestions) + 2):
                    return None  # Не объединять
                
                elif choice == str(len(suggestions) + 1):
                    custom_name = input("Введите свое название: ").strip()
                    if custom_name:
                        return custom_name
                    else:
                        print("❌ Название не может быть пустым!")
                        continue
                
                else:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(suggestions):
                        return suggestions[choice_idx]
                    else:
                        print(f"❌ Выберите число от 1 до {len(suggestions) + 2}")
                        continue
                        
            except ValueError:
                print(f"❌ Введите число от 1 до {len(suggestions) + 2}")
                continue
    
    def merge_folders(self, group, new_name):
        """Объединяет папки группы в одну с новым названием"""
        # Создаем безопасное имя для файловой системы
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)
        target_folder = self.certificates_dir / safe_name
        
        # Создаем целевую папку
        target_folder.mkdir(exist_ok=True)
        
        total_moved = 0
        
        for folder in group:
            if folder.name == safe_name:
                # Если папка уже имеет целевое название, пропускаем
                continue
                
            # Перемещаем все PDF файлы
            for pdf_file in folder.glob("*.pdf"):
                target_file = target_folder / pdf_file.name
                
                # Если файл уже существует, добавляем счетчик
                counter = 1
                while target_file.exists():
                    name_part = pdf_file.stem
                    ext_part = pdf_file.suffix
                    target_file = target_folder / f"{name_part}_{counter}{ext_part}"
                    counter += 1
                
                shutil.move(pdf_file, target_file)
                total_moved += 1
            
            # Удаляем пустую папку
            try:
                folder.rmdir()
                print(f"  🗑️  Удалена папка: {folder.name}")
            except OSError:
                print(f"  ⚠️  Не удалось удалить папку: {folder.name} (возможно, не пустая)")
        
        print(f"  ✅ Перемещено {total_moved} файлов в папку: {safe_name}")
        return total_moved
    
    def process_folder_merging(self):
        """Основной процесс объединения папок"""
        if not self.certificates_dir.exists():
            print("❌ Папка 'сертификаты' не найдена!")
            return
        
        # Получаем все папки с программами (кроме "Неопознанные")
        program_folders = [d for d in self.certificates_dir.iterdir() 
                          if d.is_dir() and d.name != "Неопознанные"]
        
        if len(program_folders) < 2:
            print("📁 Недостаточно папок для объединения!")
            return
        
        print(f"🔍 Найдено {len(program_folders)} папок с программами")
        
        # Группируем похожие папки
        groups = self.group_similar_folders(program_folders)
        
        # Фильтруем группы (оставляем только те, где больше 1 папки)
        groups_to_merge = [group for group in groups if len(group) > 1]
        
        if not groups_to_merge:
            print("🎉 Все папки уже уникальны, объединение не требуется!")
            return
        
        print(f"\n📊 Найдено {len(groups_to_merge)} групп для возможного объединения:")
        
        # Показываем информацию о каждой группе
        merging_plan = []
        
        for i, group in enumerate(groups_to_merge, 1):
            total_files = self.show_group_info(group, i)
            
            # Пользователь выбирает название или отказывается от объединения
            chosen_name = self.choose_group_name(group, i)
            
            if chosen_name:
                merging_plan.append((group, chosen_name))
                print(f"✅ Группа {i} будет объединена в: '{chosen_name}'")
            else:
                print(f"⏭️  Группа {i} пропущена")
        
        if not merging_plan:
            print("\n🤷 Нет групп для объединения.")
            return
        
        # Подтверждение операции
        print(f"\n⚠️  ВНИМАНИЕ: Будет выполнено объединение {len(merging_plan)} групп папок!")
        confirm = input("Продолжить? (да/нет): ").strip().lower()
        
        if confirm not in ['да', 'yes', 'y', 'д']:
            print("❌ Операция отменена")
            return
        
        # Выполняем объединение
        print(f"\n🔄 Начинаем объединение...")
        
        total_merged_files = 0
        for group, new_name in merging_plan:
            print(f"\n📁 Объединяем группу в: '{new_name}'")
            moved_files = self.merge_folders(group, new_name)
            total_merged_files += moved_files
        
        print(f"\n🎉 ОБЪЕДИНЕНИЕ ЗАВЕРШЕНО!")
        print(f"📁 Объединено групп: {len(merging_plan)}")
        print(f"📄 Перемещено файлов: {total_merged_files}")
        
        # Показываем финальное состояние
        self.show_final_state()
    
    def show_final_state(self):
        """Показывает финальное состояние папок"""
        program_folders = [d for d in self.certificates_dir.iterdir() 
                          if d.is_dir() and d.name != "Неопознанные"]
        
        print(f"\n📂 ФИНАЛЬНОЕ СОСТОЯНИЕ ({len(program_folders)} папок):")
        print("=" * 60)
        
        for i, folder in enumerate(program_folders, 1):
            file_count = len(list(folder.glob("*.pdf")))
            print(f"{i:2}. {folder.name} ({file_count} файлов)")

def main():
    merger = FolderMerger()
    
    print("🔗 ИНТЕРАКТИВНОЕ ОБЪЕДИНЕНИЕ ПОХОЖИХ ПАПОК")
    print("=" * 50)
    print("Этот скрипт поможет объединить похожие папки с программами.")
    print("Вы сможете выбрать названия для объединенных папок.\n")
    
    merger.process_folder_merging()

if __name__ == "__main__":
    main()