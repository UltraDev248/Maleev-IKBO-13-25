"""Эмулятор командной строки UNIX (Вариант 14)."""

import argparse
import os
import posixpath
import shlex
import tkinter as tk
from tkinter import scrolledtext
import zipfile

DEFAULT_PROMPT = "emulator$ "
WINDOW_TITLE = "UNIX Shell Emulator"
WINDOW_GEOMETRY = "750x500"


class VFS:
    """Виртуальная файловая система в оперативной памяти (in-memory)."""

    def __init__(self, zip_path: str | None = None) -> None:
        """Инициализация VFS из ZIP-архива или стандартного набора."""
        self.zip_path = zip_path
        self.cwd = "/"
        self.dirs: set[str] = {"/"}
        self.files: dict[str, set[str]] = {"/": set()}
        self.reinit()

    def reinit(self) -> None:
        """Сброс состояния виртуальной файловой системы к начальному."""
        self.cwd = "/"
        self.dirs = {"/"}
        self.files = {"/": set()}
        if self.zip_path and os.path.exists(self.zip_path):
            self._load_zip(self.zip_path)
        else:
            self._load_default()

    def _add_dir(self, dir_path: str) -> None:
        """Регистрация директории и всех ее родительских папок в памяти."""
        norm = posixpath.normpath("/" + dir_path.strip("/"))
        parts = [p for p in norm.split("/") if p]
        curr = "/"
        for part in parts:
            nxt = posixpath.join(curr, part)
            self.dirs.add(nxt)
            self.files.setdefault(curr, set()).add(part)
            self.files.setdefault(nxt, set())
            curr = nxt

    def _load_default(self) -> None:
        """Создание демонстрационной структуры каталогов по умолчанию."""
        self._add_dir("/test")
        self._add_dir("/my folder with spaces")
        self.files["/test"].add("demo.txt")
        self.files["/"].add("readme.txt")

    def _load_zip(self, zip_path: str) -> None:
        """Загрузка структуры файлов и папок из ZIP-архива в память."""
        with zipfile.ZipFile(zip_path, "r") as zf:
            for item in zf.namelist():
                clean = item.strip("/")
                if not clean:
                    continue
                if item.endswith("/"):
                    self._add_dir(clean)
                else:
                    parent = posixpath.dirname("/" + clean)
                    name = posixpath.basename(clean)
                    self._add_dir(parent)
                    self.files.setdefault(parent, set()).add(name)

    def resolve_path(self, target: str) -> str:
        """Преобразование относительного пути в нормализованный абсолютный."""
        if not target:
            return self.cwd
        raw = (
            target
            if target.startswith("/")
            else posixpath.join(self.cwd, target)
        )
        norm = posixpath.normpath(raw)
        return "/" if norm.startswith("//") else norm

    def change_dir(self, target: str) -> bool:
        """Смена текущей рабочей директории VFS."""
        resolved = self.resolve_path(target)
        if resolved in self.dirs:
            self.cwd = resolved
            return True
        return False

    def list_dir(self, target: str | None = None) -> list[str]:
        """Получение отсортированного списка элементов директории."""
        path = self.resolve_path(target) if target else self.cwd
        if path not in self.dirs:
            return []
        return sorted(list(self.files.get(path, set())))


class ShellEngine:
    """Движок разбора и выполнения команд оболочки."""

    def __init__(self, vfs: VFS) -> None:
        """Привязка VFS и регистрация обработчиков команд."""
        self.vfs = vfs
        self.handlers = {
            "exit": self._cmd_exit,
            "ls": self._cmd_ls,
            "cd": self._cmd_cd,
            "pwd": self._cmd_pwd,
            "reinit": self._cmd_reinit,
            "vfs-init": self._cmd_reinit,
            "source": self._cmd_source,
        }

    def execute(self, raw_line: str) -> tuple[bool, str]:
        """Разбор строки с учетом кавычек и вызов обработчика команды."""
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            return True, ""
        try:
            tokens = shlex.split(stripped)
        except ValueError as err:
            return False, f"Ошибка разбора: {err}"

        cmd, args = tokens[0], tokens[1:]
        handler = self.handlers.get(cmd)
        if not handler:
            return False, f"{cmd}: неизвестная команда"
        return handler(args)

    def _cmd_exit(self, args: list[str]) -> tuple[bool, str]:
        """Обработка команды выхода из эмулятора."""
        _ = args
        return True, "exit"

    def _cmd_ls(self, args: list[str]) -> tuple[bool, str]:
        """Обработка команды просмотра содержимого каталога."""
        target = args[0] if args else None
        items = self.vfs.list_dir(target)
        return True, "  ".join(items)

    def _cmd_cd(self, args: list[str]) -> tuple[bool, str]:
        """Обработка команды смены текущей директории."""
        target = args[0] if args else "/"
        if self.vfs.change_dir(target):
            return True, ""
        return False, f"cd: каталог не найден: {target}"

    def _cmd_pwd(self, args: list[str]) -> tuple[bool, str]:
        """Вывод полного пути к текущей директории."""
        _ = args
        return True, self.vfs.cwd

    def _cmd_reinit(self, args: list[str]) -> tuple[bool, str]:
        """Сброс состояния виртуальной файловой системы."""
        _ = args
        self.vfs.reinit()
        return True, "VFS сброшена в исходное состояние."

    def _cmd_source(self, args: list[str]) -> tuple[bool, str]:
        """Выполнение команд из файла скрипта с остановкой на первой ошибке."""
        if not args:
            return False, "source: укажите путь к файлу скрипта"
        script_path = args[0]
        if not os.path.exists(script_path):
            return False, f"source: файл не найден: {script_path}"

        outputs: list[str] = []
        with open(script_path, "r", encoding="utf-8") as file:
            for idx, line in enumerate(file, start=1):
                ok, out = self.execute(line)
                if out and out != "exit":
                    outputs.append(out)
                if not ok:
                    outputs.append(
                        f"[Скрипт остановлен] Ошибка на строке {idx}."
                    )
                    break
        return True, "\n".join(outputs)


class ShellGUI:
    """Графический интерфейс терминала на базе библиотеки Tkinter."""

    def __init__(
        self, engine: ShellEngine, prompt: str, script: str | None = None
    ) -> None:
        """Конфигурация главного окна и виджетов ввода-вывода."""
        self.engine = engine
        self.prompt = prompt
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_GEOMETRY)

        self.output_area = scrolledtext.ScrolledText(
            self.root, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 11)
        )
        self.output_area.pack(fill=tk.BOTH, expand=True)

        self.entry = tk.Entry(
            self.root, bg="#252526", fg="#ffffff", font=("Consolas", 11)
        )
        self.entry.pack(fill=tk.X)
        self.entry.bind("<Return>", self._on_enter)

        if script:
            self.run_startup_script(script)

    def _write_line(self, text: str) -> None:
        """Добавление строки текста в окно терминала."""
        if text:
            self.output_area.insert(tk.END, text + "\n")
            self.output_area.see(tk.END)

    def _on_enter(self, event: tk.Event) -> None:
        """Обработчик нажатия клавиши Enter в строке ввода."""
        _ = event
        cmd_line = self.entry.get()
        self.entry.delete(0, tk.END)
        self._write_line(f"{self.prompt}{cmd_line}")
        _, out = self.engine.execute(cmd_line)
        if out == "exit":
            self.root.destroy()
            return
        self._write_line(out)

    def run_startup_script(self, script_path: str) -> None:
        """Автоматический прогон стартового скрипта при открытии окна."""
        norm_path = script_path.replace("\\", "/")
        _, out = self.engine.execute(f'source "{norm_path}"')
        self._write_line(out)

    def run(self) -> None:
        """Запуск главного цикла обработки событий окна."""
        self.root.mainloop()


def parse_args() -> argparse.Namespace:
    """Разбор аргументов командной строки при запуске эмулятора."""
    parser = argparse.ArgumentParser(description=WINDOW_TITLE)
    parser.add_argument("--vfs", default=None, help="Путь к ZIP-архиву VFS")
    parser.add_argument(
        "--prompt", default=DEFAULT_PROMPT, help="Приглашение ко вводу"
    )
    parser.add_argument(
        "--script", default=None, help="Путь к стартовому скрипту"
    )
    return parser.parse_args()


def main() -> None:
    """Точка входа для запуска эмулятора."""
    args = parse_args()
    vfs = VFS(args.vfs)
    engine = ShellEngine(vfs)
    gui = ShellGUI(engine, args.prompt, args.script)
    gui.run()


if __name__ == "__main__":
    main()