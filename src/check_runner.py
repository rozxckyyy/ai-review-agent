import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.project_config import CheckConfig


MAX_OUTPUT_LENGTH = 8000


@dataclass
class CheckResult:
    name: str
    command: str
    status: str
    exit_code: int | None
    stdout: str
    stderr: str


def _truncate_output(value: str, max_length: int = MAX_OUTPUT_LENGTH) -> str:
    if len(value) <= max_length:
        return value

    return value[:max_length] + "\n\n[output truncated]"


def _resolve_working_directory(target_dir: Path, working_directory: str) -> Path:
    root = target_dir.resolve()
    candidate = (target_dir / working_directory).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise RuntimeError(
            f"Рабочая директория проверки выходит за пределы проекта: {working_directory}"
        ) from error

    if not candidate.exists():
        raise RuntimeError(f"Рабочая директория проверки не найдена: {working_directory}")

    return candidate


def run_project_checks(
    target_dir: Path,
    checks: list[CheckConfig],
) -> list[CheckResult]:
    results: list[CheckResult] = []

    for check in checks:
        try:
            cwd = _resolve_working_directory(
                target_dir=target_dir,
                working_directory=check.working_directory,
            )

            process = subprocess.run(
                check.command,
                cwd=cwd,
                shell=True,
                text=True,
                capture_output=True,
                timeout=check.timeout,
            )

            status = "passed" if process.returncode == 0 else "failed"

            results.append(
                CheckResult(
                    name=check.name,
                    command=check.command,
                    status=status,
                    exit_code=process.returncode,
                    stdout=_truncate_output(process.stdout),
                    stderr=_truncate_output(process.stderr),
                )
            )

        except subprocess.TimeoutExpired as error:
            results.append(
                CheckResult(
                    name=check.name,
                    command=check.command,
                    status="timeout",
                    exit_code=None,
                    stdout=_truncate_output(error.stdout or ""),
                    stderr=_truncate_output(error.stderr or ""),
                )
            )

        except Exception as error:
            results.append(
                CheckResult(
                    name=check.name,
                    command=check.command,
                    status="error",
                    exit_code=None,
                    stdout="",
                    stderr=str(error),
                )
            )

    return results


def all_checks_passed(results: list[CheckResult]) -> bool:
    return all(result.status == "passed" for result in results)


def format_check_results_for_prompt(results: list[CheckResult]) -> str:
    if not results:
        return "Инструментальные проверки не настроены или не запускались."

    parts: list[str] = []

    for result in results:
        parts.append(
            "\n".join(
                [
                    f'<CHECK name="{result.name}" status="{result.status}" exit_code="{result.exit_code}">',
                    "<COMMAND>",
                    result.command,
                    "</COMMAND>",
                    "<STDOUT>",
                    result.stdout.strip() or "[empty]",
                    "</STDOUT>",
                    "<STDERR>",
                    result.stderr.strip() or "[empty]",
                    "</STDERR>",
                    "</CHECK>",
                ]
            )
        )

    return "\n\n".join(parts)