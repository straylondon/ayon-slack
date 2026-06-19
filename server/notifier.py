import re
from typing import List

import httpx

_LINK_RE = re.compile(r"\[([^\]]+)\]\((?:user|version|task|folder):[^)]+\)")
_MENTION_RE = re.compile(r"\(user:([^)]+)\)")


def clean_body(text) -> str:
    """Convert AYON markup [Name](user:foo) >> Name for readable Slack text."""
    return _LINK_RE.sub(r"\1", text or "")


def mentioned_users(text) -> List[str]:
    """Usernames directly tagged in a comment body, e.g. (user:foo)."""
    return _MENTION_RE.findall(text or "")


def render(template, **values):
    try:
        return template.format(**values)
    except (KeyError, IndexError):
        return template


def origin_reference(summary):
    """Return (entity_type, entity_id) of the activity's origin entity."""
    for ref in (summary or {}).get("references") or []:
        if ref.get("reference_type") == "origin":
            return ref.get("entity_type"), ref.get("entity_id")
    return None, None


def matching_profiles(profiles, task_type, task_name):
    """Profiles whose task_types/task_names filters accept the given task.

    An empty filter list matches anything, mirroring filter_profiles.
    """
    matched = []
    for profile in profiles:
        if profile.task_types and task_type not in profile.task_types:
            continue
        if profile.task_names and task_name not in profile.task_names:
            continue
        matched.append(profile)
    return matched


async def post_message(token, channels, message, log):
    async with httpx.AsyncClient(timeout=10) as client:
        for channel in channels:
            try:
                res = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "channel": channel, 
                        "text": message
                        },
                )
                if not res.json().get("ok"):
                    log.warning(
                        f"Slack post to '{channel}' failed: "
                        f"{res.json().get('error')}")
            except Exception:
                log.warning(
                    f"Slack post to '{channel}' raised",
                    exc_info=True)
