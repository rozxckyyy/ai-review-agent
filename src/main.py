import argparse
from pathlib import Path

from src.formatter import AI_REVIEW_COMMENT_MARKER, format_review_comment
from src.gemini_client import review_diff
from src.github_client import (
    get_pull_request_diff,
    upsert_pull_request_comment,
)


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
    pr_parser.add_argument("owner", help="Владелец репозитория на GitHub.")
    pr_parser.add_argument("repo", help="Название репозитория.")
    pr_parser.add_argument("pull_number", type=int, help="Номер pull request.")
    pr_parser.add_argument(
        "--publish",
        action="store_true",
        help="Опубликовать результат ревью комментарием в pull request.",
    )

    return parser.parse_args()


def read_diff_from_file(diff_file: Path) -> str:
    if not diff_file.exists():
        raise FileNotFoundError(f"Файл не найден: {diff_file}")

    return diff_file.read_text(encoding="utf-8")


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

        review = review_diff(diff)
        print(review.model_dump_json(indent=2))

        if args.publish:
            comment = format_review_comment(review)
            upsert_pull_request_comment(
                owner=args.owner,
                repo=args.repo,
                pull_number=args.pull_number,
                body=comment,
                marker=AI_REVIEW_COMMENT_MARKER,
            )
            print("Комментарий опубликован или обновлен в pull request.")

        return

    raise RuntimeError(f"Неизвестный режим запуска: {args.mode}")


if __name__ == "__main__":
    main()