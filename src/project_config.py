from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class CheckConfig:
    name: str
    command: str
    timeout: int = 120
    working_directory: str = "."


@dataclass(frozen=True)
class AgentConfig:
    checks: list[CheckConfig]


def load_agent_config(
    target_dir: Path,
    filename: str = ".ai-agent.yml",
) -> AgentConfig:
    config_path = target_dir / filename

    if not config_path.exists():
        return AgentConfig(checks=[])

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

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

    return AgentConfig(checks=checks)