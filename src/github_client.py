from typing import Final

import requests

from src.config import GITHUB_TOKEN


GITHUB_API_BASE_URL: Final[str] = "https://api.github.com"
GITHUB_API_VERSION: Final[str] = "2026-03-10"


def _build_headers(accept: str = "application/vnd.github+json") -> dict[str, str]:
    headers = {
        "Accept": accept,
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }

    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    return headers


def _handle_github_error(response: requests.Response) -> None:
    if response.ok:
        return

    try:
        error_data = response.json()
        message = error_data.get("message", response.text)
        documentation_url = error_data.get("documentation_url")
    except ValueError:
        message = response.text
        documentation_url = None

    details = f"GitHub API error {response.status_code}: {message}"

    if documentation_url:
        details += f"\nDocs: {documentation_url}"

    if response.status_code == 401:
        raise RuntimeError(
            "GitHub отклонил токен. Проверь GITHUB_TOKEN в файле .env.\n"
            + details
        )

    if response.status_code == 403:
        raise RuntimeError(
            "GitHub запретил действие. Обычно это значит, что токену "
            "не хватает прав или он не имеет доступа к репозиторию.\n"
            + details
        )

    if response.status_code == 404:
        raise RuntimeError(
            "Ресурс не найден. Проверь owner, repo, номер PR "
            "и доступ токена к репозиторию.\n"
            + details
        )

    raise RuntimeError(details)


def get_pull_request_diff(owner: str, repo: str, pull_number: int) -> str:
    url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}/pulls/{pull_number}"

    response = requests.get(
        url,
        headers=_build_headers("application/vnd.github.v3.diff"),
        timeout=30,
    )

    _handle_github_error(response)

    return response.text


def create_pull_request_comment(
    owner: str,
    repo: str,
    pull_number: int,
    body: str,
) -> None:
    url = (
        f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}"
        f"/issues/{pull_number}/comments"
    )

    response = requests.post(
        url,
        headers=_build_headers(),
        json={"body": body},
        timeout=30,
    )

    _handle_github_error(response)

def list_pull_request_comments(
    owner: str,
    repo: str,
    pull_number: int,
) -> list[dict]:
    url = (
        f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}"
        f"/issues/{pull_number}/comments"
    )

    response = requests.get(
        url,
        headers=_build_headers(),
        timeout=30,
    )

    _handle_github_error(response)

    return response.json()


def update_pull_request_comment(
    owner: str,
    repo: str,
    comment_id: int,
    body: str,
) -> None:
    url = (
        f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}"
        f"/issues/comments/{comment_id}"
    )

    response = requests.patch(
        url,
        headers=_build_headers(),
        json={"body": body},
        timeout=30,
    )

    _handle_github_error(response)


def upsert_pull_request_comment(
    owner: str,
    repo: str,
    pull_number: int,
    body: str,
    marker: str,
) -> None:
    comments = list_pull_request_comments(
        owner=owner,
        repo=repo,
        pull_number=pull_number,
    )

    for comment in comments:
        comment_body = comment.get("body") or ""

        if marker in comment_body:
            update_pull_request_comment(
                owner=owner,
                repo=repo,
                comment_id=comment["id"],
                body=body,
            )
            return

    create_pull_request_comment(
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        body=body,
    )