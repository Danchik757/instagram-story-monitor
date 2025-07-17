#!/usr/bin/env python3
# main.py
"""
Точка входа для Instagram Story Monitor
"""
import sys
import os

# Добавляем корневую директорию в путь Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import main
import asyncio

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════╗
    ║     Instagram Story Monitor Bot       ║
    ║         by @your_telegram             ║
    ╚═══════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nБот остановлен пользователем")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        sys.exit(1)