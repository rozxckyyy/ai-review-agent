from src.schemas import AutoFixResult, ExplainResult, FixResult, ReviewResult


AI_REVIEW_COMMENT_MARKER = "<!-- ai-review-agent-review-comment -->"
AI_EXPLAIN_COMMENT_MARKER = "<!-- ai-review-agent-explain-comment -->"
AI_FIX_COMMENT_MARKER = "<!-- ai-review-agent-fix-comment -->"
AI_AUTO_FIX_COMMENT_MARKER = "<!-- ai-review-agent-auto-fix-comment -->"


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


def format_fix_comment(result: FixResult) -> str:
    lines: list[str] = [
        AI_FIX_COMMENT_MARKER,
        "## 🤖 AI Review Agent — Fix Suggestions",
        "",
        f"**Summary:** {result.summary}",
        "",
    ]

    if not result.fixes:
        lines.append("Агент не нашел безопасных исправлений, которые можно предложить автоматически.")
        return "\n".join(lines)

    lines.append("### Suggested fixes")
    lines.append("")

    for index, fix in enumerate(result.fixes, start=1):
        lines.extend(
            [
                f"#### {index}. {fix.title}",
                "",
                f"- **Файл:** `{fix.file}`",
                f"- **Строки:** `{fix.start_line}-{fix.end_line}`",
                f"- **Уверенность:** `{fix.confidence}`",
                "",
                f"**Проблема:** {fix.problem}",
                "",
                f"**Почему это исправление подходит:** {fix.explanation}",
                "",
                "**Предлагаемый код:**",
                "",
                "```",
                fix.proposed_fix,
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            "Это только предложение исправления. Агент пока не изменяет код автоматически.",
        ]
    )

    return "\n".join(lines)


def format_auto_fix_comment(
    result: AutoFixResult,
    applied: list,
    failed: list,
    commit_created: bool,
) -> str:
    lines: list[str] = [
        AI_AUTO_FIX_COMMENT_MARKER,
        "## 🤖 AI Review Agent — Auto Fix",
        "",
        f"**Summary:** {result.summary}",
        "",
    ]

    if not result.patches:
        lines.append("Агент не нашел безопасных автоисправлений.")
        return "\n".join(lines)

    lines.extend(
        [
            f"**Предложено патчей:** {len(result.patches)}",
            f"**Применено:** {len(applied)}",
            f"**Не применено:** {len(failed)}",
            "",
        ]
    )

    if applied:
        lines.append("### ✅ Applied fixes")
        lines.append("")

        for item in applied:
            lines.extend(
                [
                    f"- `{item.file}` — {item.title}",
                ]
            )

        lines.append("")

    if failed:
        lines.append("### ⚠️ Skipped fixes")
        lines.append("")

        for item in failed:
            lines.extend(
                [
                    f"- `{item.file}` — {item.title}",
                    f"  - Причина: {item.reason}",
                ]
            )

        lines.append("")

    if commit_created:
        lines.append("✅ Изменения применены и запушены в ветку pull request.")
    elif applied:
        lines.append("⚠️ Исправления были применены локально, но commit не был создан.")
    else:
        lines.append("Код не был изменен.")

    return "\n".join(lines)