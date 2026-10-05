"""
Wrapper de retrocompatibilidad para app.py.
Redirige directamente al nuevo punto de entrada modular main.py.
"""
from main import main

if __name__ == "__main__":
    main()
