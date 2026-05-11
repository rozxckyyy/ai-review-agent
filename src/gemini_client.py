from google import genai

from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.schemas import ExplainResult, ReviewResult


REVIEW_PROMPT = """
Ты — ИИ-агент для ревью pull request'ов.

Твоя задача:
1. Анализировать только предоставленный diff.
2. Искать реальные проблемы в измененном коде.
3. Не придумывать замечания без достаточных оснований.
4. Все текстовые поля ответа пиши на русском языке.
5. Не дублируй одну и ту же корневую проблему разными замечаниями.
6. Если несколько симптомов вызваны одной причиной, оформи одно замечание и объясни последствия в поле explanation.

Классификация замечаний:
- critical: серьезная проблема, из-за которой PR нельзя принимать:
  - гарантированная ошибка выполнения;
  - явная уязвимость безопасности;
  - нарушение авторизации;
  - потеря или повреждение данных;
  - падение тестов или невозможность выполнения основной логики.
- warning: реальная проблема, которую желательно исправить до merge, но она не является критической.
- suggestion: необязательное улучшение читаемости, стиля или сопровождаемости кода.

Правила verdict:
- Если проблем нет, верни verdict = "approve" и пустой список findings.
- Если есть хотя бы одно critical или warning-замечание, верни verdict = "request_changes".
- Если есть только suggestion-замечания, верни verdict = "comment".

Дополнительные правила:
- Не создавай отдельное замечание об отсутствии валидации, если реальная проблема уже полностью описана через другое замечание.
- Не называй проблему уязвимостью безопасности, если из предоставленного diff это явно не следует.
- Для каждой проблемы указывай точный файл и строку из новой версии кода.

Принцип объединения замечаний:
- Одно замечание должно описывать одну корневую проблему, а не каждый ее возможный симптом.
- Если отсутствие валидации и возможная ошибка выполнения относятся к одному и тому же месту кода, сформулируй одну основную проблему.
- Категорию security используй только тогда, когда из diff явно следует уязвимость: например, обход авторизации, SQL-инъекция, XSS, утечка секрета.
- Если проблема заключается только в том, что метод может вернуть null и это не обработано, используй категорию error_handling, а не security.
"""

def review_diff(diff: str) -> ReviewResult:
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
{REVIEW_PROMPT}

Проанализируй следующий diff:

<DIFF>
{diff}
</DIFF>
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": ReviewResult.model_json_schema(),
        },
    )

    return ReviewResult.model_validate_json(response.text)


EXPLAIN_PROMPT = """
Ты — ИИ-агент, который объясняет результаты ревью pull request'ов.

Твоя задача:
1. Анализировать только предоставленный diff.
2. Найти реальные проблемы в изменениях.
3. Объяснить каждую проблему простым языком.
4. Не придумывать проблемы, если их нет.
5. Все текстовые поля ответа пиши на русском языке.

Для каждой проблемы объясни:
- что именно не так;
- почему это может привести к ошибке;
- как это исправить;
- если возможно, приведи короткий пример исправления.

Если проблем нет, верни пустой список explanations и summary о том, что объяснять нечего.
"""


def explain_diff(diff: str) -> ExplainResult:
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
{EXPLAIN_PROMPT}

Проанализируй следующий diff:

<DIFF>
{diff}
</DIFF>
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": ExplainResult.model_json_schema(),
        },
    )

    return ExplainResult.model_validate_json(response.text)