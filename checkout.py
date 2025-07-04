#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест установки всех библиотек для обработки сертификатов
"""

def test_imports():
    """Проверяет все необходимые библиотеки"""
    print("🧪 ТЕСТ УСТАНОВКИ БИБЛИОТЕК")
    print("=" * 40)
    
    tests = [
        ("pandas", "import pandas as pd"),
        ("numpy", "import numpy as np"),
        ("opencv-python", "import cv2"),
        ("Pillow", "from PIL import Image"),
        ("requests", "import requests"),
        ("easyocr", "import easyocr"),
        ("pdf2image", "from pdf2image import convert_from_path"),
        ("torch", "import torch"),
        ("pathlib", "from pathlib import Path"),
        ("re", "import re"),
        ("json", "import json"),
        ("time", "import time"),
        ("datetime", "from datetime import datetime"),
        ("collections", "from collections import Counter"),
        ("difflib", "from difflib import SequenceMatcher"),
    ]
    
    success_count = 0
    
    for name, import_code in tests:
        try:
            exec(import_code)
            print(f"✅ {name}")
            success_count += 1
        except ImportError as e:
            print(f"❌ {name}: {e}")
        except Exception as e:
            print(f"⚠️  {name}: {e}")
    
    print("\n" + "=" * 40)
    print(f"📊 Результат: {success_count}/{len(tests)} библиотек установлено")
    
    if success_count == len(tests):
        print("🎉 ВСЕ БИБЛИОТЕКИ УСТАНОВЛЕНЫ УСПЕШНО!")
    else:
        print("❌ Не все библиотеки установлены")
        return False
    
    return True

def test_poppler():
    """Проверяет Poppler"""
    print("\n🔍 ТЕСТ POPPLER")
    print("=" * 40)
    
    try:
        from pdf2image import convert_from_path
        # Попробуем создать dummy вызов (он упадет, но это нормально)
        print("✅ pdf2image импортируется")
        
        # Проверяем наличие poppler в PATH
        import subprocess
        import os
        
        try:
            result = subprocess.run(['pdftoppm', '-h'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 or 'pdftoppm' in result.stderr:
                print("✅ Poppler найден в PATH")
                return True
            else:
                print("❌ Poppler не найден в PATH")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("❌ Poppler не установлен или не в PATH")
            return False
            
    except ImportError:
        print("❌ pdf2image не установлен")
        return False

def test_gpu():
    """Проверяет доступность GPU"""
    print("\n🚀 ТЕСТ GPU")
    print("=" * 40)
    
    try:
        import torch
        
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"✅ CUDA доступна: {gpu_name}")
            print(f"📊 Видеопамять: {torch.cuda.get_device_properties(0).total_memory // 1024**3} GB")
            return True
        else:
            print("⚠️  CUDA недоступна, будет использоваться CPU")
            print("💡 Для ускорения установите CUDA: https://pytorch.org/get-started/locally/")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки GPU: {e}")
        return False

def test_easyocr():
    """Проверяет EasyOCR"""
    print("\n👁️  ТЕСТ EASYOCR")
    print("=" * 40)
    
    try:
        import easyocr
        print("✅ EasyOCR импортируется")
        
        # Попробуем создать reader (это может занять время при первом запуске)
        print("🔄 Инициализация EasyOCR...")
        reader = easyocr.Reader(['ru'], gpu=False, verbose=False)
        print("✅ EasyOCR инициализирован успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка EasyOCR: {e}")
        return False

def main():
    """Запуск всех тестов"""
    print("🔧 ПРОВЕРКА ГОТОВНОСТИ СИСТЕМЫ")
    print("Для обработки PDF сертификатов")
    print("=" * 50)
    
    all_good = True
    
    # Тест библиотек
    if not test_imports():
        all_good = False
    
    # Тест Poppler
    if not test_poppler():
        all_good = False
        print("\n💡 КАК УСТАНОВИТЬ POPPLER:")
        print("1. Скачайте: https://github.com/oschwartz10612/poppler-windows/releases/latest")
        print("2. Распакуйте в C:\\poppler\\")
        print("3. Добавьте в PATH: C:\\poppler\\Library\\bin")
        print("4. Перезапустите командную строку")
    
    # Тест GPU (необязательный)
    test_gpu()
    
    # Тест EasyOCR (может занять время)
    print("\n⚠️  Следующий тест может занять несколько минут при первом запуске...")
    input("Нажмите Enter для продолжения или Ctrl+C для выхода...")
    test_easyocr()
    
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 СИСТЕМА ГОТОВА К РАБОТЕ!")
        print("✅ Можете запускать скрипты обработки сертификатов")
    else:
        print("❌ СИСТЕМА НЕ ГОТОВА")
        print("🔧 Исправьте ошибки выше и запустите тест снова")

if __name__ == "__main__":
    main()