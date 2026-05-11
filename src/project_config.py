from dataclasses import dataclass, field
from pathlib import Path

import yaml


DEFAULT_CONTEXT_EXCLUDES = [
    ".git/**",
    ".venv/**",
    "venv/**",
    "__pycache__/**",
    ".pytest_cache/**",
    "node_modules/**",
    "vendor/**",
    "dist/**",
    "build/**",
]


@dataclass(frozen=True)
class CheckConfig:
    name: str
    command: str
    timeout: int = 120
    working_directory: str = "."


@dataclass(frozen=True)
class ContextConfig:
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=lambda: DEFAULT_CONTEXT_EXCLUDES.copy())
    max_chars_per_file: int = 20000
    max_files: int = 40


@dataclass(frozen=True)
class AgentConfig:
    checks: list[CheckConfig]
    context: ContextConfig


def _read_list(value, field_name: str) -> list[str]:
    if value is None:
        return []

    if not isinstance(value, list):
        raise RuntimeError(f"Поле {field_name} должно быть списком.")

    return [str(item) for item in value]


def _load_checks(data: dict) -> list[CheckConfig]:
    raw_checks = data.get("checks") or []

    if not isinstance(raw_checks, list):
        raise RuntimeError("В .ai-agent.yml поле checks должно быть списком.")

    checks: list[CheckConfig] = []

    for index, item in enumerate(raw_checks, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Проверка #{index} должна быть объектом.")

        command = item.get("command")

        if not command:
            raise RuntimeError(f"У проверки #{index} не указано поле command.")

        checks.append(
            CheckConfig(
                name=str(item.get("name") or f"Check {index}"),
                command=str(command),
                timeout=int(item.get("timeout", 120)),
                working_directory=str(item.get("working_directory", ".")),
            )
        )

    return checks


def _load_context(data: dict) -> ContextConfig:
    raw_context = data.get("context") or {}

    if not isinstance(raw_context, dict):
        raise RuntimeError("В .ai-agent.yml поле context должно быть объектом.")

    include = _read_list(raw_context.get("include"), "context.include")
    user_exclude = _read_list(raw_context.get("exclude"), "context.exclude")

    exclude = DEFAULT_CONTEXT_EXCLUDES.copy()
    exclude.extend(user_exclude)

    return ContextConfig(
        include=include,
        exclude=exclude,
        max_chars_per_file=int(raw_context.get("max_chars_per_file", 20000)),
        max_files=int(raw_context.get("max_files", 40)),
    )


def load_agent_config(
    target_dir: Path,
    filename: str = ".ai-agent.yml",
) -> AgentConfig:
    config_path = target_dir / filename

    if not config_path.exists():
        return AgentConfig(
            checks=[],
            context=ContextConfig(),
        )

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    if not isinstance(data, dict):
        raise RuntimeError(".ai-agent.yml должен содержать YAML-объект.")

    return AgentConfig(
        checks=_load_checks(data),
        context=_load_context(data),
    )