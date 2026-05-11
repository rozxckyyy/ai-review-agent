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

        content = absolute_path.read_text(encoding="utf-8", errors="replace")

        if len(content) > max_chars_per_file:
            content = content[:max_chars_per_file]
            content += "\n\n/* Файл обрезан из-за большого размера */"

        parts.append(
            f"<FILE path=\"{file_path}\">\n{content}\n</FILE>"
        )

    return "\n\n".join(parts)