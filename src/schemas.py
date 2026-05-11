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


class FixSuggestion(BaseModel):
    title: str = Field(description="Короткий заголовок исправления.")
    file: str = Field(description="Файл, в котором предлагается исправление.")
    start_line: int = Field(description="Начальная строка проблемного участка.")
    end_line: int = Field(description="Конечная строка проблемного участка.")
    problem: str = Field(description="Описание проблемы, которую исправляет предложение.")
    proposed_fix: str = Field(description="Предлагаемый исправленный код.")
    explanation: str = Field(description="Почему это исправление подходит.")
    confidence: float = Field(
        ge=0,
        le=1,
        description="Уверенность модели в исправлении от 0 до 1.",
    )


class FixResult(BaseModel):
    summary: str = Field(description="Краткий итог предложенных исправлений.")
    fixes: list[FixSuggestion] = Field(
        description="Список предложенных исправлений."
    )


class AutoFixPatch(BaseModel):
    title: str = Field(description="Короткий заголовок автоисправления.")
    file: str = Field(description="Файл, который нужно изменить.")
    start_line: int = Field(
        ge=1,
        description="Начальная строка фрагмента, который нужно заменить. Нумерация с 1.",
    )
    end_line: int = Field(
        ge=1,
        description="Конечная строка фрагмента, который нужно заменить. Нумерация с 1.",
    )
    original_code: str = Field(
        description="Точный фрагмент текущего кода, который нужно заменить."
    )
    replacement_code: str = Field(
        description="Код, на который нужно заменить original_code."
    )
    explanation: str = Field(description="Почему это исправление безопасно.")
    confidence: float = Field(
        ge=0,
        le=1,
        description="Уверенность модели в исправлении от 0 до 1.",
    )
    risk: Literal["low", "medium", "high"] = Field(
        description="Оценка риска исправления."
    )


class AutoFixResult(BaseModel):
    summary: str = Field(description="Краткий итог автоисправлений.")
    patches: list[AutoFixPatch] = Field(
        description="Список патчей, которые можно попробовать применить."
    )