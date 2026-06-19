from __future__ import annotations

from typing import Any

from ayon_server.addons import BaseServerAddon
from ayon_server.entities import TaskEntity, VersionEntity
from ayon_server.events import EventStream
from ayon_server.logging import logger

from .settings import (
    SlackSettings,
    DEFAULT_SLACK_SETTING,
    convert_settings_overrides,
)
from .notifier import (
    clean_body,
    matching_profiles,
    mentioned_users,
    origin_reference,
    post_message,
    render,
)


class Slack(BaseServerAddon):

    settings_model = SlackSettings

    def initialize(self) -> None:
        self._subscriptions: dict[str, str] = {}
        super().initialize()

    async def setup(self):
        await self._sync_subscriptions()

    async def on_settings_changed(self, *args, **kwargs):
        await self._sync_subscriptions()

    async def _sync_subscriptions(self):
        """Subscribe to topics only for features enabled in studio settings."""
        settings = await self.get_studio_settings()
        events = getattr(settings, "events", None)
        enabled = bool(settings and settings.enabled)
        features = (
            ("activity.created",
             enabled and events and events.comment_mentions.enabled,
             self._on_comment),
            ("entity.task.assignees_changed",
             enabled and events and events.task_assignments.enabled,
             self._on_assignees),
        )
        for topic, active, handler in features:
            token = self._subscriptions.get(topic)
            if active and not token:
                self._subscriptions[topic] = EventStream.subscribe(
                    topic, handler)
            elif not active and token:
                EventStream.unsubscribe(token)
                self._subscriptions.pop(topic, None)

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_SLACK_SETTING)

    async def convert_settings_overrides(
        self,
        source_version: str,
        overrides: dict[str, Any],
    ) -> dict[str, Any]:
        await convert_settings_overrides(source_version, overrides)
        return await super().convert_settings_overrides(
            source_version, overrides
        )

    async def _feature_settings(self, event):
        """Return (settings, token) if the addon is enabled for the project."""
        if not event.project:
            return None, None

        settings = await self.get_project_settings(event.project)
        if not settings or not settings.enabled or not settings.token:
            return None, None

        return settings, settings.token

    async def _resolve_task(self, project, entity_type, entity_id):
        """Load the task an activity/event relates to, if any."""
        if not entity_id:
            return None

        try:
            if entity_type == "task":
                return await TaskEntity.load(project, entity_id)
            if entity_type == "version":
                version = await VersionEntity.load(project, entity_id)
                if version and version.task_id:
                    return await TaskEntity.load(project, version.task_id)
        except Exception:
            logger.debug(
                f"Could not resolve task for {entity_type} {entity_id}",
                exc_info=True)
        return None

    async def _post_profiles(self, token, profiles, values):
        for profile in profiles:
            for channel_message in profile.channel_messages:
                message = render(channel_message.message, **values)
                await post_message(
                    token, channel_message.channels, message, logger)

    async def _on_comment(self, event) -> None:
        settings, token = await self._feature_settings(event)
        if not settings:
            return

        cfg = settings.events.comment_mentions
        if not cfg.enabled or not cfg.profiles:
            return

        if (event.summary or {}).get("activity_type") != "comment":
            return

        body = (event.payload or {}).get("body", "")
        targets = mentioned_users(body)
        if not targets:
            return

        entity_type, entity_id = origin_reference(event.summary)
        task = await self._resolve_task(event.project, entity_type, entity_id)
        profiles = matching_profiles(
            cfg.profiles,
            task.task_type if task else None,
            task.name if task else None)

        values = dict[str, str](
            project=event.project, user=event.user or "",
            targets=", ".join(targets), body=clean_body(body))
        await self._post_profiles(token, profiles, values)

    async def _on_assignees(self, event) -> None:
        settings, token = await self._feature_settings(event)
        if not settings:
            return

        cfg = settings.events.task_assignments
        if not cfg.enabled or not cfg.profiles:
            return

        payload = event.payload or {}
        added = set[Any](payload.get("newValue") or []) - set[Any](
            payload.get("oldValue") or [])
        if not added:
            return

        task = await self._resolve_task(
            event.project, "task", (event.summary or {}).get("entityId"))
        profiles = matching_profiles(
            cfg.profiles,
            task.task_type if task else None,
            task.name if task else None)

        values = dict[str, str](
            project=event.project, user=event.user or "",
            targets=", ".join(sorted(added)),
            task=(task.label or task.name) if task else "")
        await self._post_profiles(token, profiles, values)
