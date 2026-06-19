from ayon_server.settings import (
    SettingsField,
    BaseSettingsModel,
    task_types_enum,
)


class CommentMentionMessage(BaseSettingsModel):
    channels: list[str] = SettingsField(
        default_factory=list,
        title="Channels"
    )
    message: str = SettingsField(
        "{user} tagged {targets} in a comment on {project}:\n{body}",
        title="Message",
        widget="textarea"
    )


class CommentMentionProfile(BaseSettingsModel):
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = SettingsField(
        default_factory=list,
        title="Task names"
    )
    _desc = "Available placeholders: {user}, {targets}, {body}, {project}"
    channel_messages: list[CommentMentionMessage] = SettingsField(
        default_factory=list,
        title="Messages to channels",
        description=_desc,
        section="Messages"
    )


class CommentMentionNotification(BaseSettingsModel):
    """Notify when a comment directly tags a user."""
    _isGroup = True
    enabled: bool = SettingsField(False, title="Enabled")
    profiles: list[CommentMentionProfile] = SettingsField(
        default_factory=list,
        title="Profiles"
    )


class TaskAssignmentMessage(BaseSettingsModel):
    channels: list[str] = SettingsField(
        default_factory=list,
        title="Channels"
    )
    message: str = SettingsField(
        "{user} assigned {targets} to {task} on {project}",
        title="Message",
        widget="textarea"
    )


class TaskAssignmentProfile(BaseSettingsModel):
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = SettingsField(
        default_factory=list,
        title="Task names"
    )
    _desc = "Available placeholders: {user}, {targets}, {task}, {project}"
    channel_messages: list[TaskAssignmentMessage] = SettingsField(
        default_factory=list,
        title="Messages to channels",
        description=_desc,
        section="Messages"
    )


class TaskAssignmentNotification(BaseSettingsModel):
    """Notify when a user is assigned to a task."""
    _isGroup = True
    enabled: bool = SettingsField(False, title="Enabled")
    profiles: list[TaskAssignmentProfile] = SettingsField(
        default_factory=list,
        title="Profiles"
    )


class SlackEventSettings(BaseSettingsModel):
    comment_mentions: CommentMentionNotification = SettingsField(
        default_factory=CommentMentionNotification,
        title="Comment mentions"
    )
    task_assignments: TaskAssignmentNotification = SettingsField(
        default_factory=TaskAssignmentNotification,
        title="Task assignments"
    )
