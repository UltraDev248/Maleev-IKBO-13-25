"""Модульные тесты для визуализатора графа зависимостей (Вариант 14)."""

import os
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.visualizer import (
    Config,
    build_dependency_graph_bfs,
    compute_load_order,
    generate_mermaid,
    parse_ini_config,
    parse_nuspec_dependencies,
    save_graph_to_svg,
)


class TestStage1Configuration(unittest.TestCase):
    """Тестирование чтения и валидации INI-конфигурации."""

    def test_valid_ini_parsing(self) -> None:
        """Проверка считывания корректного INI-файла."""
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            tmp.write(
                "[settings]\n"
                "package_name = TestPkg\n"
                "package_version = 1.0\n"
                "repo_url = https://test.org\n"
                "test_mode = true\n"
                "output_image = test.svg\n"
                "ascii_tree = true\n"
            )
            tmp_path = tmp.name

        try:
            cfg = parse_ini_config(tmp_path)
            self.assertEqual(cfg.package_name, "TestPkg")
            self.assertTrue(cfg.test_mode)
            self.assertTrue(cfg.ascii_tree)
        finally:
            os.remove(tmp_path)

    def test_missing_required_fields_error(self) -> None:
        """Проверка выброса исключения при пустом package_name."""
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            tmp.write(
                "[settings]\npackage_name =\nrepo_url = https://x.org\n"
            )
            tmp_path = tmp.name

        try:
            with self.assertRaises(ValueError):
                parse_ini_config(tmp_path)
        finally:
            os.remove(tmp_path)


class TestStage2NuspecParsing(unittest.TestCase):
    """Тестирование разбора метаданных NuGet .nuspec."""

    def test_parse_dependencies(self) -> None:
        """Проверка парсинга XML без учета пространств имен."""
        xml_data = (
            b'<?xml version="1.0"?>'
            b'<package xmlns="http://schemas.microsoft.com/nuspec.xsd">'
            b"  <metadata>"
            b"    <dependencies>"
            b'      <group targetFramework=".NETStandard2.0">'
            b'        <dependency id="Microsoft.CSharp" version="4.7.0" />'
            b'        <dependency id="System.Buffers" version="4.5.1" />'
            b"      </group>"
            b"    </dependencies>"
            b"  </metadata>"
            b"</package>"
        )
        deps = parse_nuspec_dependencies(xml_data)
        self.assertEqual(deps, ["Microsoft.CSharp", "System.Buffers"])


class TestStage3BFSAndCycles(unittest.TestCase):
    """Тестирование алгоритма BFS и обработки циклических зависимостей."""

    def _create_repo_config(self) -> tuple[str, Config]:
        """Создание временного файла графа и конфигурации."""
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            tmp.write("A: B C\nB: D\nC: E\nD: A\nE:\n")
            repo_file = tmp.name

        config = Config(
            package_name="A",
            package_version="1.0",
            repo_url=repo_file,
            test_mode=True,
            output_image="out.svg",
            ascii_tree=False,
        )
        return repo_file, config

    def test_bfs_traversal(self) -> None:
        """Проверка полного сбора транзитивных зависимостей."""
        repo_file, config = self._create_repo_config()
        try:
            graph, _ = build_dependency_graph_bfs(config, "A")
            self.assertEqual(set(graph.keys()), {"A", "B", "C", "D", "E"})
        finally:
            if os.path.exists(repo_file):
                os.remove(repo_file)

    def test_cycle_detection(self) -> None:
        """Проверка фиксации цикла D -> A."""
        repo_file, config = self._create_repo_config()
        try:
            _, cycles = build_dependency_graph_bfs(config, "A")
            self.assertIn(("D", "A"), cycles)
        finally:
            if os.path.exists(repo_file):
                os.remove(repo_file)


class TestStage4LoadOrder(unittest.TestCase):
    """Тестирование расчета порядка загрузки зависимостей."""

    def test_load_order_resolution(self) -> None:
        """Проверка порядка загрузки зависимости D раньше пакета B."""
        graph = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": [],
            "D": [],
        }
        order = compute_load_order(graph, "A")
        self.assertLess(order.index("D"), order.index("B"))
        self.assertLess(order.index("B"), order.index("A"))


class TestStage5Visualization(unittest.TestCase):
    """Тестирование генерации Mermaid и SVG."""

    def test_mermaid_generation(self) -> None:
        """Проверка формата Mermaid-диаграммы."""
        graph = {"A": ["B"], "B": []}
        mermaid = generate_mermaid(graph)
        self.assertIn("graph TD", mermaid)
        self.assertIn("A --> B", mermaid)

    def test_svg_file_creation(self) -> None:
        """Проверка корректной записи SVG-файла."""
        graph = {"A": ["B"], "B": []}
        out_svg = os.path.join(tempfile.gettempdir(), "test_diag.svg")
        try:
            save_graph_to_svg(graph, "A", out_svg)
            self.assertTrue(os.path.exists(out_svg))
            with open(out_svg, "r", encoding="utf-8") as file:
                content = file.read()
                self.assertIn("<svg", content)
                self.assertIn("</svg>", content)
        finally:
            if os.path.exists(out_svg):
                os.remove(out_svg)


if __name__ == "__main__":
    unittest.main()