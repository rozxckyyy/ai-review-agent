import argparse
from pathlib import Path

from src.formatter import (
    AI_EXPLAIN_COMMENT_MARKER,
    AI_FIX_COMMENT_MARKER,
    AI_REVIEW_COMMENT_MARKER,
    format_explain_comment,
    format_fix_comment,
    format_review_comment,
)
from src.gemini_client import explain_diff, propose_fixes, review_diff
from src.github_client import get_pull_request_diff, upsert_pull_request_comment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ИИ-агент для анализа diff-файлов и GitHub pull request."
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    file_parser = subparsers.add_parser(
        "file",
        help="Проанализировать diff из локального файла.",
    )
    file_parser.add_argument(
        "diff_file",
        type=Path,
        help="Путь к файлу с diff.",
    )

    pr_parser = subparsers.add_parser(
        "pr",
        help="Проанализировать diff pull request из GitHub.",
    )
    pr_parser.add_argument(
        "owner",
        help="Владелец репозитория на GitHub.",
    )
    pr_parser.add_argument(
        "repo",
        help="Название репозитория.",
    )
    pr_parser.add_argument(
        "pull_number",
        type=int,
        help="Номер pull request.",
    )
    pr_parser.add_argument(
        "--publish",
        action="store_true",
        help="Опубликовать результат в pull request.",
    )
    pr_parser.add_argument(
        "--command",
        choices=["review", "explain", "fix"],
        default="review",
        help="Команда агента: review, explain или fix.",
    )

    return parser.parse_args()


def read_diff_from_file(diff_file: Path) -> str:
    if not diff_file.exists():
        raise FileNotFoundError(f"Файл не найден: {diff_file}")

    return diff_file.read_text(encoding="utf-8")


def run_review_command(
    owner: str,
    repo: str,
    pull_number: int,
    diff: str,
    publish: bool,
) -> None:
    review = review_diff(diff)

    print(review.model_dump_json(indent=2))

    if not publish:
        return

    comment = format_review_comment(review)

    upsert_pull_request_comment(
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        body=comment,
        marker=AI_REVIEW_COMMENT_MARKER,
    )

    print("Комментарий ревью опубликован или обновлен в pull request.")


def run_explain_command(
    owner: str,
    repo: str,
    pull_number: int,
    diff: str,
    publish: bool,
) -> None:
    explanation = explain_diff(diff)

    print(explanation.model_dump_json(indent=2))

    if not publish:
        return

    comment = format_explain_comment(explanation)

    upsert_pull_request_comment(
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        body=comment,
        marker=AI_EXPLAIN_COMMENT_MARKER,
    )

    print("Комментарий с объяснением опубликован или обновлен в pull request.")


def run_fix_command(
    owner: str,
    repo: str,
    pull_number: int,
    diff: str,
    publish: bool,
) -> None:
    fixes = propose_fixes(diff)

    print(fixes.model_dump_json(indent=2))

    if not publish:
        return

    comment = format_fix_comment(fixes)

    upsert_pull_request_comment(
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        body=comment,
        marker=AI_FIX_COMMENT_MARKER,
    )

    print("Комментарий с предложениями исправлений опубликован или обновлен в pull request.")


def main() -> None:
    args = parse_args()

    if args.mode == "file":
        diff = read_diff_from_file(args.diff_file)
        review = review_diff(diff)

        print(review.model_dump_json(indent=2))
        return

    if args.mode == "pr":
        diff = get_pull_request_diff(
            owner=args.owner,
            repo=args.repo,
            pull_number=args.pull_number,
        )

        if args.command == "review":
            run_review_command(
                owner=args.owner,
                repo=args.repo,
                pull_number=args.pull_number,
                diff=diff,
                publish=args.publish,
            )
            return

        if args.command == "explain":
            run_explain_command(
                owner=args.owner,
                repo=args.repo,
                pull_number=args.pull_number,
                diff=diff,
                publish=args.publish,
            )
            return

        if args.command == "fix":
            run_fix_command(
                owner=args.owner,
                repo=args.repo,
                pull_number=args.pull_number,
                diff=diff,
                publish=args.publish,
            )
            return

        raise RuntimeError(f"Неизвестная команда агента: {args.command}")

    raise RuntimeError(f"Неизвестный режим запуска: {args.mode}")


if __name__ == "__main__":
    main()