"""Пакет эмулятора командной строки UNIX-подобной ОС."""

from src.emulator import VFS, ShellEngine, ShellGUI, main

__all__ = ["VFS", "ShellEngine", "ShellGUI", "main"]
__version__ = "0.1.0"