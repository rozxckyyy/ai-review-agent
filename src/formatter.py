from src.schemas import ReviewResult, ExplainResult


AI_REVIEW_COMMENT_MARKER = "<!-- ai-review-agent-comment -->"
AI_EXPLAIN_COMMENT_MARKER = "<!-- ai-review-agent-explain-comment -->"


def format_review_comment(review: ReviewResult) -> str:
    verdict_label = {
        "approve": "✅ Approve",
        "comment": "💬 Comment",
        "request_changes": "❌ Request changes",
    }[review.verdict]

    lines: list[str] = [
        AI_REVIEW_COMMENT_MARKER,
        "## 🤖 AI Review Agent",
        "",
        f"**Verdict:** {verdict_label}",
        "",
        f"**Summary:** {review.summary}",
        "",
    ]

    if not review.findings:
        lines.append("Замечаний не найдено.")
        return "\n".join(lines)

    lines.append("### Findings")
    lines.append("")

    for index, finding in enumerate(review.findings, start=1):
        lines.extend(
            [
                f"#### {index}. [{finding.severity}] {finding.title}",
                "",
                f"- **Категория:** `{finding.category}`",
                f"- **Файл:** `{finding.file}`",
                f"- **Строка:** `{finding.line}`",
                f"- **Уверенность:** `{finding.confidence}`",
                "",
                finding.message,
                "",
                f"**Пояснение:** {finding.explanation}",
                "",
            ]
        )

    return "\n".join(lines)



def format_explain_comment(result: ExplainResult) -> str:
    lines: list[str] = [
        AI_EXPLAIN_COMMENT_MARKER,
        "## 🤖 AI Review Agent — Explain",
        "",
        f"**Summary:** {result.summary}",
        "",
    ]

    if not result.explanations:
        lines.append("Подробных замечаний для объяснения не найдено.")
        return "\n".join(lines)

    lines.append("### Explanations")
    lines.append("")

    for index, explanation in enumerate(result.explanations, start=1):
        lines.extend(
            [
                f"#### {index}. {explanation.title}",
                "",
                f"- **Файл:** `{explanation.file}`",
                f"- **Строка:** `{explanation.line}`",
                "",
                f"**Что не так:** {explanation.plain_explanation}",
                "",
                f"**Почему это важно:** {explanation.why_it_matters}",
                "",
                f"**Как исправить:** {explanation.how_to_fix}",
                "",
            ]
        )

        if explanation.example_fix:
            lines.extend(
                [
                    "**Пример исправления:**",
                    "",
                    "```",
                    explanation.example_fix,
                    "```",
                    "",
                ]
            )

    return "\n".join(lines)