from dataclasses import dataclass
from pathlib import Path

from src.schemas import AutoFixPatch


@dataclass
class AppliedPatch:
    title: str
    file: str


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

        if not patch.original_code.strip():
            failed.append(
                FailedPatch(
                    title=patch.title,
                    file=patch.file,
                    reason="Пустой original_code.",
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
        occurrences = content.count(patch.original_code)

        if occurrences == 0:
            failed.append(
                FailedPatch(
                    title=patch.title,
                    file=patch.file,
                    reason="Фрагмент original_code не найден в файле.",
                )
            )
            continue

        if occurrences > 1:
            failed.append(
                FailedPatch(
                    title=patch.title,
                    file=patch.file,
                    reason="Фрагмент original_code найден больше одного раза. Автоисправление небезопасно.",
                )
            )
            continue

        updated_content = content.replace(
            patch.original_code,
            patch.replacement_code,
            1,
        )

        file_path.write_text(updated_content, encoding="utf-8")

        applied.append(
            AppliedPatch(
                title=patch.title,
                file=patch.file,
            )
        )

    return applied, failed