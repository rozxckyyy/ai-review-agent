import subprocess
from pathlib import Path


def _run_git(target_dir: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=target_dir,
        text=True,
        capture_output=True,
        check=True,
    )

    return result.stdout.strip()


def configure_git_author(target_dir: Path) -> None:
    _run_git(target_dir, ["config", "user.name", "AI Review Agent"])
    _run_git(
        target_dir,
        ["config", "user.email", "github-actions[bot]@users.noreply.github.com"],
    )


def has_git_changes(target_dir: Path) -> bool:
    status = _run_git(target_dir, ["status", "--porcelain"])
    return bool(status.strip())


def commit_and_push_changes(target_dir: Path, message: str) -> bool:
    configure_git_author(target_dir)

    if not has_git_changes(target_dir):
        return False

    _run_git(target_dir, ["add", "."])
    _run_git(target_dir, ["commit", "-m", message])

    branch = _run_git(target_dir, ["rev-parse", "--abbrev-ref", "HEAD"])

    if branch and branch != "HEAD":
        _run_git(target_dir, ["push", "origin", f"HEAD:{branch}"])
    else:
        _run_git(target_dir, ["push"])

    return True