"""Модульные тесты для эмулятора командной строки UNIX (Этапы 1–3).

Все тесты изолированы от графического интерфейса Tkinter и проверяют
логику VFS, движка команд ShellEngine и парсера аргументов CLI.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.emulator import VFS, ShellEngine, parse_args


class TestStage1REPLAndParser(unittest.TestCase):
    """Тестирование разбора команд и базового цикла REPL (Этап 1)."""

    def _create_engine(self) -> tuple[VFS, ShellEngine]:
        """Создание нового экземпляра VFS и движка для теста."""
        vfs = VFS()
        return vfs, ShellEngine(vfs)

    def test_shlex_parsing_quotes(self) -> None:
        """Проверка разбора аргументов с пробелами внутри кавычек."""
        vfs, engine = self._create_engine()
        ok, _ = engine.execute('cd "my folder with spaces"')
        self.assertTrue(ok)
        self.assertEqual(vfs.cwd, "/my folder with spaces")

    def test_unknown_command(self) -> None:
        """Проверка сообщения об ошибке при вызове неизвестной команды."""
        _, engine = self._create_engine()
        ok, out = engine.execute("unregistered_util 123 -a")
        self.assertFalse(ok)
        self.assertIn("неизвестная команда", out)

    def test_exit_command(self) -> None:
        """Проверка распознавания команды завершения работы."""
        _, engine = self._create_engine()
        ok, out = engine.execute("exit")
        self.assertTrue(ok)
        self.assertEqual(out, "exit")

    def test_empty_and_comment_lines(self) -> None:
        """Проверка игнорирования пустых строк и комментариев."""
        _, engine = self._create_engine()
        ok_empty, out_empty = engine.execute("    ")
        self.assertTrue(ok_empty)
        self.assertEqual(out_empty, "")

        comment_cmd = chr(35) + " тестовая строка"
        ok_comment, out_comment = engine.execute(comment_cmd)
        self.assertTrue(ok_comment)
        self.assertEqual(out_comment, "")


class TestStage2CLIAndScripts(unittest.TestCase):
    """Тестирование параметров CLI и выполнения скриптов (Этап 2)."""

    def test_cli_arguments_parsing(self) -> None:
        """Проверка считывания параметров --vfs, --prompt и --script."""
        fake_argv = [
            "emulator.py",
            "--vfs",
            "vfs_samples/archive.zip",
            "--prompt",
            "custom_sh$ ",
            "--script",
            "tests/script_ok.txt",
        ]
        with patch("sys.argv", fake_argv):
            args = parse_args()
            self.assertEqual(args.vfs, "vfs_samples/archive.zip")
            self.assertEqual(args.prompt, "custom_sh$ ")
            self.assertEqual(args.script, "tests/script_ok.txt")

    def test_script_execution_success(self) -> None:
        """Проверка последовательного выполнения команд из скрипта."""
        vfs = VFS()
        engine = ShellEngine(vfs)

        with tempfile.NamedTemporaryFile(
            "w+",
            delete=False,
            encoding="utf-8",
        ) as tmp_file:
            tmp_file.write("cd test\nls\n")
            tmp_path = tmp_file.name.replace("\\", "/")

        try:
            ok, out = engine.execute(f'source "{tmp_path}"')
            self.assertTrue(ok)
            self.assertIn("demo.txt", out)
            self.assertEqual(vfs.cwd, "/test")
        finally:
            if os.path.exists(tmp_file.name):
                os.remove(tmp_file.name)

    def test_script_execution_stops_on_error(self) -> None:
        """Проверка аварийного останова скрипта на первой ошибочной строке."""
        vfs = VFS()
        engine = ShellEngine(vfs)

        with tempfile.NamedTemporaryFile(
            "w+",
            delete=False,
            encoding="utf-8",
        ) as tmp_file:
            tmp_file.write("cd test\nbad_command_call\ncd /\n")
            tmp_path = tmp_file.name.replace("\\", "/")

        try:
            ok, out = engine.execute(f'source "{tmp_path}"')
            self.assertTrue(ok)
            self.assertIn("[Скрипт остановлен] Ошибка на строке 2.", out)
            self.assertEqual(vfs.cwd, "/test")
        finally:
            if os.path.exists(tmp_file.name):
                os.remove(tmp_file.name)


class TestStage3VFSAndNavigation(unittest.TestCase):
    """Тестирование виртуальной файловой системы в памяти (Этап 3)."""

    def _create_sample_zip(self) -> str:
        """Создание временного ZIP-архива для проверки загрузки VFS."""
        tmp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        zip_path = tmp_zip.name
        tmp_zip.close()

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("var/log/syslog.log", "system logs")
            zf.writestr("etc/config.json", '{"mode": "test"}')
            zf.writestr("home/user/document.txt", "hello world")
        return zip_path

    def test_vfs_loads_into_memory(self) -> None:
        """Проверка загрузки структуры каталогов ZIP в оперативную память."""
        zip_path = self._create_sample_zip()
        try:
            vfs = VFS(zip_path)
            self.assertEqual(vfs.list_dir(), ["etc", "home", "var"])
        finally:
            if os.path.exists(zip_path):
                os.remove(zip_path)

    def test_vfs_cd_relative_and_absolute(self) -> None:
        """Проверка навигации по абсолютным и относительным путям."""
        zip_path = self._create_sample_zip()
        try:
            vfs = VFS(zip_path)
            self.assertTrue(vfs.change_dir("home"))
            self.assertEqual(vfs.cwd, "/home")

            self.assertTrue(vfs.change_dir("user"))
            self.assertEqual(vfs.cwd, "/home/user")
            self.assertEqual(vfs.list_dir(), ["document.txt"])

            self.assertTrue(vfs.change_dir("/"))
            self.assertEqual(vfs.cwd, "/")
        finally:
            if os.path.exists(zip_path):
                os.remove(zip_path)

    def test_vfs_cd_parent_directory(self) -> None:
        """Проверка перехода на уровень выше через 'cd ..'."""
        zip_path = self._create_sample_zip()
        try:
            vfs = VFS(zip_path)
            vfs.change_dir("/var/log")
            vfs.change_dir("..")
            self.assertEqual(vfs.cwd, "/var")

            vfs.change_dir("..")
            self.assertEqual(vfs.cwd, "/")

            vfs.change_dir("..")
            self.assertEqual(vfs.cwd, "/")
        finally:
            if os.path.exists(zip_path):
                os.remove(zip_path)

    def test_vfs_cd_nonexistent_directory(self) -> None:
        """Проверка отказа перехода в несуществующую директорию."""
        zip_path = self._create_sample_zip()
        try:
            vfs = VFS(zip_path)
            self.assertFalse(vfs.change_dir("missing_directory"))
            self.assertEqual(vfs.cwd, "/")
        finally:
            if os.path.exists(zip_path):
                os.remove(zip_path)

    def test_vfs_reinit(self) -> None:
        """Проверка сброса состояния файловой системы командой reinit."""
        zip_path = self._create_sample_zip()
        try:
            vfs = VFS(zip_path)
            vfs.change_dir("/var/log")
            vfs.reinit()
            self.assertEqual(vfs.cwd, "/")
        finally:
            if os.path.exists(zip_path):
                os.remove(zip_path)


if __name__ == "__main__":
    unittest.main()