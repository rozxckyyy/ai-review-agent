from typing import Literal

from pydantic import BaseModel, Field


class Finding(BaseModel):
    severity: Literal["critical", "warning", "suggestion"] = Field(
        description="Критичность замечания."
    )
    category: Literal[
        "correctness",
        "security",
        "validation",
        "error_handling",
        "style",
        "tests",
    ] = Field(description="Категория замечания.")
    file: str = Field(description="Путь к файлу, где найдена проблема.")
    line: int = Field(description="Номер строки в новой версии файла.")
    title: str = Field(description="Короткий заголовок замечания.")
    message: str = Field(description="Краткое описание проблемы.")
    explanation: str = Field(description="Почему это считается проблемой.")
    confidence: float = Field(
        ge=0,
        le=1,
        description="Уверенность модели в замечании от 0 до 1.",
    )


class ReviewResult(BaseModel):
    verdict: Literal["approve", "comment", "request_changes"] = Field(
        description="Итоговая рекомендация по pull request."
    )
    summary: str = Field(description="Краткий итог ревью.")
    findings: list[Finding] = Field(
        description="Список найденных замечаний."
    )

class FindingExplanation(BaseModel):
    title: str = Field(description="Короткий заголовок объясняемой проблемы.")
    file: str = Field(description="Файл, к которому относится проблема.")
    line: int = Field(description="Строка, к которой относится проблема.")
    plain_explanation: str = Field(description="Простое объяснение проблемы.")
    why_it_matters: str = Field(description="Почему это важно.")
    how_to_fix: str = Field(description="Как можно исправить проблему.")
    example_fix: str = Field(
        description="Краткий пример исправления. Если пример не нужен, верни пустую строку."
    )


class ExplainResult(BaseModel):
    summary: str = Field(description="Краткий итог объяснения.")
    explanations: list[FindingExplanation] = Field(
        description="Подробные объяснения найденных проблем."
    )