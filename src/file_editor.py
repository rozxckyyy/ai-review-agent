from dataclasses import dataclass
from pathlib import Path

from src.schemas import AutoFixPatch


MAX_LINE_REPLACEMENT_SPAN = 80


@dataclass
class AppliedPatch:
    title: str
    file: str
    method: str


@dataclass
class FailedPatch:
    title: str
    file: str
    reason: str


def _resolve_safe_path(target_dir: Path, file_path: str) -> Path:
    root = target_dir.resolve()
    candidate = (target_dir / file_path).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise RuntimeError(
            f"Небезопасный путь к файлу за пределами проекта: {file_path}"
        ) from error

    return candidate


def _normalize_line_endings(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _replace_exact(
    content: str,
    patch: AutoFixPatch,
) -> tuple[str | None, str | None]:
    original_code = _normalize_line_endings(patch.original_code)
    normalized_content = _normalize_line_endings(content)

    occurrences = normalized_content.count(original_code)

    if occurrences == 1:
        updated_content = normalized_content.replace(
            original_code,
            _normalize_line_endings(patch.replacement_code),
            1,
        )
        return updated_content, None

    if occurrences == 0:
        return None, "Фрагмент original_code не найден в файле."

    return None, "Фрагмент original_code найден больше одного раза. Автоисправление небезопасно."


def _replace_by_line_range(
    content: str,
    patch: AutoFixPatch,
) -> tuple[str | None, str | None]:
    if patch.start_line > patch.end_line:
        return None, "Некорректный диапазон строк: start_line больше end_line."

    span = patch.end_line - patch.start_line + 1

    if span > MAX_LINE_REPLACEMENT_SPAN:
        return None, (
            f"Диапазон строк слишком большой для безопасной замены: {span} строк."
        )

    normalized_content = _normalize_line_endings(content)
    lines = normalized_content.splitlines(keepends=True)

    if patch.start_line > len(lines):
        return None, (
            f"start_line выходит за пределы файла: {patch.start_line}, "
            f"в файле строк: {len(lines)}."
        )

    if patch.end_line > len(lines):
        return None, (
            f"end_line выходит за пределы файла: {patch.end_line}, "
            f"в файле строк: {len(lines)}."
        )

    start_index = patch.start_line - 1
    end_index = patch.end_line

    replacement = _normalize_line_endings(patch.replacement_code)

    if replacement and not replacement.endswith("\n"):
        replacement += "\n"

    replacement_lines = replacement.splitlines(keepends=True)

    updated_lines = [
        *lines[:start_index],
        *replacement_lines,
        *lines[end_index:],
    ]

    return "".join(updated_lines), None


def apply_auto_fix_patches(
    target_dir: Path,
    patches: list[AutoFixPatch],
    min_confidence: float = 0.8,
) -> tuple[list[AppliedPatch], list[FailedPatch]]:
    applied: list[AppliedPatch] = []
    failed: list[FailedPatch] = []

    for patch in patches:
        if patch.confidence < min_confidence:
            failed.append(
                FailedPatch(
                    title=patch.title,
                    file=patch.file,
                    reason=f"Низкая уверенность модели: {patch.confidence}",
                )
            )
            continue

        if patch.risk != "low":
            failed.append(
                FailedPatch(
                    title=patch.title,
                    file=patch.file,
                    reason=f"Исправление имеет риск `{patch.risk}`, разрешен только `low`.",
                )
            )
            continue

        if not patch.replacement_code.strip():
            failed.append(
                FailedPatch(
                    title=patch.title,
                    file=patch.file,
                    reason="Пустой replacement_code.",
                )
            )
            continue

        try:
            file_path = _resolve_safe_path(target_dir, patch.file)
        except RuntimeError as error:
            failed.append(
                FailedPatch(
                    title=patch.title,
                    file=patch.file,
                    reason=str(error),
                )
            )
            continue

        if not file_path.exists():
            failed.append(
                FailedPatch(
                    title=patch.title,
                    file=patch.file,
                    reason="Файл не найден.",
                )
            )
            continue

        content = file_path.read_text(encoding="utf-8", errors="replace")

        updated_content: str | None = None
        exact_error: str | None = None

        if patch.original_code.strip():
            updated_content, exact_error = _replace_exact(
                content=content,
                patch=patch,
            )

        if updated_content is not None:
            file_path.write_text(updated_content, encoding="utf-8")
            applied.append(
                AppliedPatch(
                    title=patch.title,
                    file=patch.file,
                    method="exact",
                )
            )
            continue

        line_updated_content, line_error = _replace_by_line_range(
            content=content,
            patch=patch,
        )

        if line_updated_content is not None:
            file_path.write_text(line_updated_content, encoding="utf-8")
            applied.append(
                AppliedPatch(
                    title=patch.title,
                    file=patch.file,
                    method="line-range",
                )
            )
            continue

        reason = line_error or exact_error or "Не удалось применить патч."

        failed.append(
            FailedPatch(
                title=patch.title,
                file=patch.file,
                reason=reason,
            )
        )

    return applied, failed