import argparse
from pathlib import Path

from src.check_runner import (
    all_checks_passed,
    format_check_results_for_prompt,
    run_project_checks,
)
from src.diff_utils import (
    build_file_context,
    collect_context_file_paths,
    extract_changed_file_paths,
    merge_unique_file_paths,
)
from src.file_editor import apply_auto_fix_patches
from src.formatter import (
    AI_AUTO_FIX_COMMENT_MARKER,
    AI_EXPLAIN_COMMENT_MARKER,
    AI_FIX_COMMENT_MARKER,
    AI_REVERT_COMMENT_MARKER,
    AI_REVIEW_COMMENT_MARKER,
    format_auto_fix_comment,
    format_explain_comment,
    format_fix_comment,
    format_revert_comment,
    format_review_comment,
)
from src.gemini_client import (
    explain_diff,
    propose_auto_fixes,
    propose_fixes,
    review_diff,
)
from src.git_service import commit_and_push_changes, revert_last_auto_fix_commit
from src.github_client import get_pull_request_diff, upsert_pull_request_comment
from src.project_config import load_agent_config


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
        help="Опубликовать результат в pull request.",
    )
    pr_parser.add_argument(
        "--command",
        choices=["review", "explain", "fix", "auto-fix", "revert-last-fix"],
        default="review",
        help="Команда агента: review, explain, fix, auto-fix или revert-last-fix.",
    )
    pr_parser.add_argument(
        "--target-dir",
        type=Path,
        default=None,
        help="Путь к checkout репозитория.",
    )
    pr_parser.add_argument(
        "--fail-on-request-changes",
        action="store_true",
        help="Завершить процесс с ошибкой, если review verdict = request_changes.",
    )

    return parser.parse_args()


def read_diff_from_file(diff_file: Path) -> str:
    if not diff_file.exists():
        raise FileNotFoundError(f"Файл не найден: {diff_file}")

    return diff_file.read_text(encoding="utf-8")


def collect_project_checks(target_dir: Path | None):
    if target_dir is None:
        return [], "Инструментальные проверки не запускались: --target-dir не передан."

    if not target_dir.exists():
        return [], f"Инструментальные проверки не запускались: target-dir не найден: {target_dir}"

    config = load_agent_config(target_dir)

    if not config.checks:
        return [], "Инструментальные проверки не настроены: файл .ai-agent.yml не найден или checks пуст."

    results = run_project_checks(
        target_dir=target_dir,
        checks=config.checks,
    )

    return results, format_check_results_for_prompt(results)


def collect_project_file_context(
    target_dir: Path | None,
    diff: str,
) -> str:
    if target_dir is None:
        return "Дополнительный контекст файлов не собран: --target-dir не передан."

    if not target_dir.exists():
        return f"Дополнительный контекст файлов не собран: target-dir не найден: {target_dir}"

    config = load_agent_config(target_dir)

    changed_files = extract_changed_file_paths(diff)

    included_files = collect_context_file_paths(
        target_dir=target_dir,
        include_patterns=config.context.include,
        exclude_patterns=config.context.exclude,
        max_files=config.context.max_files,
    )

    context_files = merge_unique_file_paths(
        changed_files,
        included_files,
    )

    return build_file_context(
        target_dir=target_dir,
        file_paths=context_files,
        max_chars_per_file=config.context.max_chars_per_file,
    )


def run_review_command(
    owner: str,
    repo: str,
    pull_number: int,
    diff: str,
    publish: bool,
    target_dir: Path | None,
    fail_on_request_changes: bool,
) -> None:
    check_results, checks_context = collect_project_checks(target_dir)
    file_context = collect_project_file_context(target_dir, diff)

    review = review_diff(
        diff=diff,
        checks_context=checks_context,
        file_context=file_context,
    )

    print(review.model_dump_json(indent=2))

    if publish:
        comment = format_review_comment(
            review=review,
            check_results=check_results,
        )

        upsert_pull_request_comment(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            body=comment,
            marker=AI_REVIEW_COMMENT_MARKER,
        )

        print("Комментарий ревью опубликован или обновлен в pull request.")

    if fail_on_request_changes and review.verdict == "request_changes":
        raise SystemExit(1)


def run_explain_command(
    owner: str,
    repo: str,
    pull_number: int,
    diff: str,
    publish: bool,
    target_dir: Path | None,
) -> None:
    _, checks_context = collect_project_checks(target_dir)
    file_context = collect_project_file_context(target_dir, diff)

    explanation = explain_diff(
        diff=diff,
        checks_context=checks_context,
        file_context=file_context,
    )

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
    target_dir: Path | None,
) -> None:
    _, checks_context = collect_project_checks(target_dir)
    file_context = collect_project_file_context(target_dir, diff)

    fixes = propose_fixes(
        diff=diff,
        checks_context=checks_context,
        file_context=file_context,
    )

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


def run_auto_fix_command(
    owner: str,
    repo: str,
    pull_number: int,
    diff: str,
    publish: bool,
    target_dir: Path | None,
) -> None:
    if target_dir is None:
        raise RuntimeError("Для команды auto-fix необходимо передать --target-dir.")

    if not target_dir.exists():
        raise FileNotFoundError(f"target-dir не найден: {target_dir}")

    _, checks_context = collect_project_checks(target_dir)
    file_context = collect_project_file_context(target_dir, diff)

    auto_fixes = propose_auto_fixes(
        diff=diff,
        file_context=file_context,
        checks_context=checks_context,
    )

    applied, failed = apply_auto_fix_patches(
        target_dir=target_dir,
        patches=auto_fixes.patches,
    )

    post_check_results = []
    checks_passed: bool | None = None
    commit_created = False

    if applied:
        config = load_agent_config(target_dir)

        if config.checks:
            post_check_results = run_project_checks(
                target_dir=target_dir,
                checks=config.checks,
            )
            checks_passed = all_checks_passed(post_check_results)
        else:
            checks_passed = True

        if checks_passed:
            changed_by_agent = [patch.file for patch in applied]

            commit_created = commit_and_push_changes(
                target_dir=target_dir,
                message="Apply AI auto-fix suggestions",
                file_paths=changed_by_agent,
            )

    print(auto_fixes.model_dump_json(indent=2))
    print(f"Applied fixes: {len(applied)}")
    print(f"Failed fixes: {len(failed)}")
    print(f"Checks passed: {checks_passed}")
    print(f"Commit created: {commit_created}")

    if publish:
        comment = format_auto_fix_comment(
            result=auto_fixes,
            applied=applied,
            failed=failed,
            commit_created=commit_created,
            check_results=post_check_results,
            checks_passed=checks_passed,
        )

        upsert_pull_request_comment(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            body=comment,
            marker=AI_AUTO_FIX_COMMENT_MARKER,
        )

        print("Комментарий auto-fix опубликован или обновлен в pull request.")

    if applied and checks_passed is False:
        raise SystemExit(1)


def run_revert_last_fix_command(
    owner: str,
    repo: str,
    pull_number: int,
    publish: bool,
    target_dir: Path | None,
) -> None:
    if target_dir is None:
        raise RuntimeError("Для команды revert-last-fix необходимо передать --target-dir.")

    if not target_dir.exists():
        raise FileNotFoundError(f"target-dir не найден: {target_dir}")

    reverted_commit: str | None = None
    error: str | None = None

    try:
        reverted_commit = revert_last_auto_fix_commit(target_dir)
    except Exception as exception:
        error = str(exception)

    print(f"Reverted commit: {reverted_commit}")
    print(f"Error: {error}")

    if publish:
        comment = format_revert_comment(
            reverted_commit=reverted_commit,
            error=error,
        )

        upsert_pull_request_comment(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            body=comment,
            marker=AI_REVERT_COMMENT_MARKER,
        )

        print("Комментарий revert-last-fix опубликован или обновлен в pull request.")

    if error:
        raise RuntimeError(error)


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
                target_dir=args.target_dir,
                fail_on_request_changes=args.fail_on_request_changes,
            )
            return

        if args.command == "explain":
            run_explain_command(
                owner=args.owner,
                repo=args.repo,
                pull_number=args.pull_number,
                diff=diff,
                publish=args.publish,
                target_dir=args.target_dir,
            )
            return

        if args.command == "fix":
            run_fix_command(
                owner=args.owner,
                repo=args.repo,
                pull_number=args.pull_number,
                diff=diff,
                publish=args.publish,
                target_dir=args.target_dir,
            )
            return

        if args.command == "auto-fix":
            run_auto_fix_command(
                owner=args.owner,
                repo=args.repo,
                pull_number=args.pull_number,
                diff=diff,
                publish=args.publish,
                target_dir=args.target_dir,
            )
            return

        if args.command == "revert-last-fix":
            run_revert_last_fix_command(
                owner=args.owner,
                repo=args.repo,
                pull_number=args.pull_number,
                publish=args.publish,
                target_dir=args.target_dir,
            )
            return

        raise RuntimeError(f"Неизвестная команда агента: {args.command}")

    raise RuntimeError(f"Неизвестный режим запуска: {args.mode}")


if __name__ == "__main__":
    main()