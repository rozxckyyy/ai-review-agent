import subprocess
from pathlib import Path


AUTO_FIX_COMMIT_MESSAGE = "Apply AI auto-fix suggestions"
AI_AGENT_AUTHOR_NAME = "AI Review Agent"


def _run_git(target_dir: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=target_dir,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Ошибка выполнения git-команды:\n"
            f"git {' '.join(args)}\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )

    return result.stdout.strip()


def _run_git_allow_error(target_dir: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=target_dir,
        text=True,
        capture_output=True,
    )


def configure_git_author(target_dir: Path) -> None:
    _run_git(target_dir, ["config", "user.name", AI_AGENT_AUTHOR_NAME])
    _run_git(
        target_dir,
        ["config", "user.email", "github-actions[bot]@users.noreply.github.com"],
    )


def has_git_changes(target_dir: Path) -> bool:
    status = _run_git(target_dir, ["status", "--porcelain"])
    return bool(status.strip())


def has_staged_changes(target_dir: Path) -> bool:
    result = _run_git_allow_error(
        target_dir,
        ["diff", "--cached", "--quiet"],
    )

    return result.returncode == 1


def get_current_branch(target_dir: Path) -> str:
    branch = _run_git(target_dir, ["rev-parse", "--abbrev-ref", "HEAD"])

    if not branch or branch == "HEAD":
        raise RuntimeError("Не удалось определить текущую ветку для push.")

    return branch


def push_current_branch(target_dir: Path) -> None:
    branch = get_current_branch(target_dir)
    _run_git(target_dir, ["push", "origin", f"HEAD:{branch}"])


def _unique_paths(file_paths: list[str]) -> list[str]:
    result: list[str] = []

    for file_path in file_paths:
        normalized = file_path.replace("\\", "/")

        if normalized not in result:
            result.append(normalized)

    return result


def commit_and_push_changes(
    target_dir: Path,
    message: str,
    file_paths: list[str] | None = None,
) -> bool:
    configure_git_author(target_dir)

    if file_paths is None:
        if not has_git_changes(target_dir):
            return False

        _run_git(target_dir, ["add", "."])
    else:
        paths = _unique_paths(file_paths)

        if not paths:
            return False

        _run_git(target_dir, ["add", "--", *paths])

    if not has_staged_changes(target_dir):
        return False

    _run_git(target_dir, ["commit", "-m", message])
    push_current_branch(target_dir)

    return True


def find_last_auto_fix_commit(target_dir: Path, max_count: int = 30) -> str | None:
    log_output = _run_git(
        target_dir,
        [
            "log",
            f"--max-count={max_count}",
            "--format=%H%x1f%an%x1f%s",
        ],
    )

    if not log_output.strip():
        return None

    for line in log_output.splitlines():
        parts = line.split("\x1f")

        if len(parts) != 3:
            continue

        commit_hash, author_name, subject = parts

        if author_name == AI_AGENT_AUTHOR_NAME and subject == AUTO_FIX_COMMIT_MESSAGE:
            return commit_hash

    return None


def revert_last_auto_fix_commit(target_dir: Path) -> str | None:
    configure_git_author(target_dir)

    commit_hash = find_last_auto_fix_commit(target_dir)

    if commit_hash is None:
        return None

    _run_git(target_dir, ["revert", "--no-edit", commit_hash])
    push_current_branch(target_dir)

    return commit_hash