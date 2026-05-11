from fnmatch import fnmatch
from pathlib import Path


def extract_changed_file_paths(diff: str) -> list[str]:
    paths: list[str] = []

    for line in diff.splitlines():
        if not line.startswith("+++ b/"):
            continue

        path = line.removeprefix("+++ b/").strip()

        if path == "/dev/null":
            continue

        if path not in paths:
            paths.append(path)

    return paths


def merge_unique_file_paths(*groups: list[str]) -> list[str]:
    result: list[str] = []

    for group in groups:
        for file_path in group:
            normalized = file_path.replace("\\", "/")

            if normalized not in result:
                result.append(normalized)

    return result


def _is_safe_relative_pattern(pattern: str) -> bool:
    normalized = pattern.replace("\\", "/")

    if normalized.startswith("/"):
        return False

    parts = normalized.split("/")

    return ".." not in parts


def _is_safe_child_path(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _matches_any_pattern(file_path: str, patterns: list[str]) -> bool:
    normalized = file_path.replace("\\", "/")

    return any(fnmatch(normalized, pattern) for pattern in patterns)


def collect_context_file_paths(
    target_dir: Path,
    include_patterns: list[str],
    exclude_patterns: list[str],
    max_files: int = 40,
) -> list[str]:
    paths: list[str] = []

    for pattern in include_patterns:
        if not _is_safe_relative_pattern(pattern):
            continue

        for candidate in target_dir.glob(pattern):
            if len(paths) >= max_files:
                return paths

            if not candidate.is_file():
                continue

            if not _is_safe_child_path(target_dir, candidate):
                continue

            relative_path = candidate.relative_to(target_dir).as_posix()

            if _matches_any_pattern(relative_path, exclude_patterns):
                continue

            if relative_path not in paths:
                paths.append(relative_path)

    return paths


def build_file_context(
    target_dir: Path,
    file_paths: list[str],
    max_chars_per_file: int = 20000,
) -> str:
    parts: list[str] = []

    for file_path in file_paths:
        absolute_path = target_dir / file_path

        if not absolute_path.exists() or not absolute_path.is_file():
            continue

        if not _is_safe_child_path(target_dir, absolute_path):
            continue

        content = absolute_path.read_text(encoding="utf-8", errors="replace")

        if len(content) > max_chars_per_file:
            content = content[:max_chars_per_file]
            content += "\n\n/* Файл обрезан из-за большого размера */"

        parts.append(
            f'<FILE path="{file_path}">\n{content}\n</FILE>'
        )

    if not parts:
        return "Контекст файлов не передан."

    return "\n\n".join(parts)