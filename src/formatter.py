from src.schemas import ReviewResult


def format_review_comment(review: ReviewResult) -> str:
    verdict_label = {
        "approve": "✅ Approve",
        "comment": "💬 Comment",
        "request_changes": "❌ Request changes",
    }[review.verdict]

    lines: list[str] = [
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