"""Инструмент визуализации графа зависимостей NuGet (Вариант 14)."""

import collections
import configparser
import os
import sys
import urllib.error
import urllib.request
from xml.etree import ElementTree as xml_tree

HTTP_OK = 200
CANVAS_WIDTH = 900
CANVAS_HEIGHT = 650
NODE_RADIUS = 28
LEVEL_SPACING = 120
FONT_SIZE = 12
BOX_MARGIN = 40
LAST_OFFSET = 1


class Config:
    """Хранилище настроек приложения из конфигурационного файла INI."""

    def __init__(
        self,
        package_name: str,
        package_version: str,
        repo_url: str,
        test_mode: bool,
        output_image: str,
        ascii_tree: bool,
    ) -> None:
        """Инициализация параметров конфигурации."""
        self.package_name = package_name
        self.package_version = package_version
        self.repo_url = repo_url
        self.test_mode = test_mode
        self.output_image = output_image
        self.ascii_tree = ascii_tree

    def display(self) -> None:
        """Вывод параметров в формате ключ-значение (Этап 1)."""
        print("=== Параметры конфигурации (Этап 1) ===")
        print(f"package_name:    {self.package_name}")
        print(f"package_version: {self.package_version}")
        print(f"repo_url:        {self.repo_url}")
        print(f"test_mode:       {self.test_mode}")
        print(f"output_image:    {self.output_image}")
        print(f"ascii_tree:      {self.ascii_tree}")
        print("========================================")


def parse_ini_config(file_path: str) -> Config:
    """Чтение и валидация конфигурационного файла формата INI."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Конфигурационный файл не найден: {file_path}"
        )

    parser = configparser.ConfigParser()
    parser.read(file_path, encoding="utf-8")

    section = "settings"
    if not parser.has_section(section):
        raise ValueError(f"Секция [{section}] отсутствует в файле.")

    pkg_name = parser.get(section, "package_name", fallback="").strip()
    pkg_ver = parser.get(section, "package_version", fallback="").strip()
    repo_url = parser.get(section, "repo_url", fallback="").strip()
    out_img = parser.get(section, "output_image", fallback="graph.svg").strip()

    if not pkg_name:
        raise ValueError("Параметр 'package_name' не может быть пустым.")
    if not repo_url:
        raise ValueError("Параметр 'repo_url' не может быть пустым.")

    test_mode = parser.getboolean(section, "test_mode", fallback=False)
    ascii_tree = parser.getboolean(section, "ascii_tree", fallback=False)

    return Config(
        pkg_name, pkg_ver, repo_url, test_mode, out_img, ascii_tree
    )


def parse_nuspec_dependencies(xml_content: bytes) -> list[str]:
    """Извлечение идентификаторов зависимостей из XML-содержимого .nuspec."""
    root = xml_tree.fromstring(xml_content)
    dependencies: set[str] = set()

    for elem in root.iter():
        tag_name = elem.tag.split("}")[-1]
        if tag_name == "dependency":
            dep_id = elem.attrib.get("id")
            if dep_id:
                dependencies.add(dep_id)

    return sorted(list(dependencies))


def fetch_nuget_dependencies(
    repo_url: str, package_name: str, version: str
) -> list[str]:
    """Получение списка прямых зависимостей пакета через NuGet API."""
    base = repo_url.rstrip("/")
    pkg = package_name.lower()
    ver = version.lower() if version else ""

    if not ver:
        return []

    nuspec_url = f"{base}/{pkg}/{ver}/{pkg}.nuspec"
    req = urllib.request.Request(
        nuspec_url, headers={"User-Agent": "DepVisualizer/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status != HTTP_OK:
                return []
            content = response.read()
            return parse_nuspec_dependencies(content)
    except (urllib.error.URLError, TimeoutError, xml_tree.ParseError):
        return []


def load_test_repository(file_path: str) -> dict[str, list[str]]:
    """Загрузка графа зависимостей из текстового файла тестового режима."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл тестового репо не найден: {file_path}")

    graph: dict[str, list[str]] = {}
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            node = parts[0].strip()
            deps = parts[1].strip().split() if parts[1:] else []
            graph[node] = deps
    return graph


def get_direct_dependencies(config: Config, package: str) -> list[str]:
    """Получение прямых зависимостей для пакета с учетом режима работы."""
    if config.test_mode:
        test_graph = load_test_repository(config.repo_url)
        return test_graph.get(package, [])
    return fetch_nuget_dependencies(
        config.repo_url, package, config.package_version
    )


def build_dependency_graph_bfs(
    config: Config, root_package: str
) -> tuple[dict[str, list[str]], set[tuple[str, str]]]:
    """Построение полного графа зависимостей алгоритмом BFS без рекурсии."""
    graph: dict[str, list[str]] = {}
    visited_nodes: set[str] = {root_package}
    queue: collections.deque[str] = collections.deque([root_package])
    cycles: set[tuple[str, str]] = set()
    test_data = (
        load_test_repository(config.repo_url) if config.test_mode else {}
    )

    while queue:
        current = queue.popleft()
        deps = (
            test_data.get(current, [])
            if config.test_mode
            else fetch_nuget_dependencies(
                config.repo_url, current, config.package_version
            )
        )
        graph[current] = deps
        for dep in deps:
            if dep in visited_nodes:
                cycles.add((current, dep))
            else:
                visited_nodes.add(dep)
                queue.append(dep)

    return graph, cycles


def compute_load_order(
    graph: dict[str, list[str]], root_package: str
) -> list[str]:
    """Определение порядка загрузки пакетов (обратный топологический)."""
    visited: set[str] = set()
    order: list[str] = []

    def dfs(node: str, in_stack: set[str]) -> None:
        visited.add(node)
        in_stack.add(node)
        for dep in graph.get(node, []):
            if dep not in visited:
                dfs(dep, in_stack)
        in_stack.remove(node)
        order.append(node)

    if root_package in graph:
        dfs(root_package, set())

    return order


def generate_mermaid(graph: dict[str, list[str]]) -> str:
    """Генерация текстового описания графа на языке Mermaid."""
    lines = ["graph TD"]
    for src_pkg, targets in sorted(graph.items()):
        if not targets:
            lines.append(f"    {src_pkg}")
        for dst_pkg in targets:
            lines.append(f"    {src_pkg} --> {dst_pkg}")
    return "\n".join(lines)


def print_ascii_tree(
    graph: dict[str, list[str]],
    current: str,
    prefix: str = "",
    visited: set[str] | None = None,
) -> None:
    """Вывод дерева зависимостей в формате псевдографики ASCII."""
    if visited is None:
        visited = set()
        print(current)

    visited.add(current)
    deps = graph.get(current, [])
    count = len(deps)

    for idx, dep in enumerate(deps):
        is_last = idx == count - LAST_OFFSET
        connector = "└── " if is_last else "├── "
        child_prefix = prefix + ("    " if is_last else "│   ")

        if dep in visited:
            print(f"{prefix}{connector}{dep} (цикл)")
        else:
            print(f"{prefix}{connector}{dep}")
            print_ascii_tree(graph, dep, child_prefix, set(visited))


def _calculate_node_positions(
    graph: dict[str, list[str]], root: str
) -> dict[str, tuple[int, int]]:
    """Расчет декартовых координат узлов по уровням BFS."""
    positions: dict[str, tuple[int, int]] = {}
    levels: dict[int, list[str]] = collections.defaultdict(list)
    depth_map: dict[str, int] = {root: 0}
    queue: collections.deque[str] = collections.deque([root])

    while queue:
        curr = queue.popleft()
        depth = depth_map[curr]
        levels[depth].append(curr)
        for dep in graph.get(curr, []):
            if dep not in depth_map:
                depth_map[dep] = depth + 1
                queue.append(dep)

    for depth, nodes in levels.items():
        y_pos = BOX_MARGIN + depth * LEVEL_SPACING
        col_width = (CANVAS_WIDTH - 2 * BOX_MARGIN) // (len(nodes) + 1)
        for idx, node in enumerate(nodes):
            x_pos = BOX_MARGIN + (idx + 1) * col_width
            positions[node] = (x_pos, y_pos)

    return positions


def _build_svg_edges(
    graph: dict[str, list[str]], coords: dict[str, tuple[int, int]]
) -> list[str]:
    """Формирование SVG-элементов линий связей между узлами графа."""
    edges: list[str] = []
    for src_pkg, deps in graph.items():
        if src_pkg not in coords:
            continue
        x1, y1 = coords[src_pkg]
        for dst_pkg in deps:
            if dst_pkg in coords:
                x2, y2 = coords[dst_pkg]
                edges.append(
                    f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                    f'stroke="#555" stroke-width="2" '
                    f'marker-end="url(#arrow)" />'
                )
    return edges


def _build_svg_nodes(coords: dict[str, tuple[int, int]]) -> list[str]:
    """Формирование SVG-элементов окружностей и подписей узлов графа."""
    nodes: list[str] = []
    for node, (pos_x, pos_y) in coords.items():
        nodes.append(
            f'  <circle cx="{pos_x}" cy="{pos_y}" r="{NODE_RADIUS}" '
            f'fill="#E3F2FD" stroke="#1565C0" stroke-width="2" />'
        )
        nodes.append(
            f'  <text x="{pos_x}" y="{pos_y + 4}" '
            f'font-size="{FONT_SIZE}" text-anchor="middle" '
            f'font-family="sans-serif">{node}</text>'
        )
    return nodes


def save_graph_to_svg(
    graph: dict[str, list[str]], root: str, output_path: str
) -> None:
    """Построение и сохранение векторного изображения графа в SVG-файл."""
    coords = _calculate_node_positions(graph, root)
    svg_elements: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}">',
        "  <defs>",
        '    <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
        '      <path d="M 0 0 L 10 5 L 0 10 z" fill="#333333" />',
        "    </marker>",
        "  </defs>",
    ]
    svg_elements.extend(_build_svg_edges(graph, coords))
    svg_elements.extend(_build_svg_nodes(coords))
    svg_elements.append("</svg>")

    with open(output_path, "w", encoding="utf-8") as file:
        file.write("\n".join(svg_elements))


def _run_pipeline(config: Config) -> None:
    """Выполнение этапов анализа и визуализации зависимостей."""
    print("\n--- Этап 2: Прямые зависимости пакета ---")
    direct_deps = get_direct_dependencies(config, config.package_name)
    print(f"Пакет: {config.package_name}")
    print(f"Прямые зависимости: {', '.join(direct_deps) or 'нет'}")

    print("\n--- Этап 3: Построение графа (BFS) ---")
    graph, cycles = build_dependency_graph_bfs(config, config.package_name)
    print(f"Всего узлов в графе: {len(graph)}")
    print(f"Циклы: {cycles}" if cycles else "Циклы не обнаружены.")

    print("\n--- Этап 4: Порядок загрузки зависимостей ---")
    load_order = compute_load_order(graph, config.package_name)
    print(" -> ".join(load_order))

    print("\n--- Этап 5: Визуализация ---")
    print("Диаграмма Mermaid:\n" + generate_mermaid(graph))
    save_graph_to_svg(graph, config.package_name, config.output_image)
    print(f"Изображение успешно сохранено в: {config.output_image}")

    if config.ascii_tree:
        print("\nДерево зависимостей (ASCII):")
        print_ascii_tree(graph, config.package_name)


def main() -> None:
    """Точка входа CLI-приложения визуализатора зависимостей."""
    config_file = sys.argv[1] if sys.argv[1:] else "config.ini"

    try:
        config = parse_ini_config(config_file)
    except (FileNotFoundError, ValueError) as err:
        print(f"Ошибка конфигурации: {err}")
        sys.exit(1)

    config.display()
    _run_pipeline(config)


if __name__ == "__main__":
    main()