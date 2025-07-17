#!/usr/bin/env python3
import sys
import os

print("Starting run.py...")
print("Current directory:", os.getcwd())
print("Python version:", sys.version)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
print("Added to path:", os.path.dirname(os.path.abspath(__file__)))

print("Importing src.main...")
try:
    from src.main import main
    print("Import successful!")
except Exception as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

import asyncio

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════╗
    ║     Instagram Story Monitor Bot       ║
    ║         Starting...                   ║
    ╚═══════════════════════════════════════╝
    """)
    
    try:
        print("Running main()...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nБот остановлен пользователем")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        import traceback
        traceback.print_exc()