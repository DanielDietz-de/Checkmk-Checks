#!/usr/bin/env python3
"""Agent Bakery rule for the Oxidized backup verifier."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    List,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import (
    LengthInRange,
    MatchRegex,
    NumberInRange,
    ValidationError,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _absolute_path(title: str, default: str | None = None) -> String:
    return String(
        title=Title(title),
        prefill=DefaultValue(default if default is not None else "/"),
        custom_validate=(
            LengthInRange(min_value=1, max_value=4096),
            MatchRegex(
                regex=r"^/.*",
                error_msg=Message("Enter an absolute path."),
            ),
        ),
    )


def _authentication() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Authentication"),
        help_text=Help(
            "Credentials are not stored in this rule. Reference a protected secret "
            "file that already exists on the Oxidized host."
        ),
        elements=(
            CascadingSingleChoiceElement(
                name="none",
                title=Title("No authentication"),
                parameter_form=FixedValue(value=None),
            ),
            CascadingSingleChoiceElement(
                name="bearer",
                title=Title("Bearer token from file"),
                parameter_form=Dictionary(
                    elements={
                        "token_file": DictElement(
                            parameter_form=_absolute_path("Bearer-token file"),
                            required=True,
                        ),
                    },
                ),
            ),
            CascadingSingleChoiceElement(
                name="basic",
                title=Title("HTTP basic authentication from file"),
                parameter_form=Dictionary(
                    elements={
                        "username": DictElement(
                            parameter_form=String(
                                title=Title("HTTP user name"),
                                custom_validate=(
                                    LengthInRange(min_value=1, max_value=256),
                                ),
                            ),
                            required=True,
                        ),
                        "password_file": DictElement(
                            parameter_form=_absolute_path("Password file"),
                            required=True,
                        ),
                    },
                ),
            ),
        ),
        prefill=DefaultValue("none"),
    )


def _endpoint(title: str, default_url: str, *, allow_file: bool) -> Dictionary:
    pattern = r"^(?:https?|file)://.+" if allow_file else r"^https?://.+"
    schemes = "HTTPS, HTTP, or file" if allow_file else "HTTPS or HTTP"
    return Dictionary(
        title=Title(title),
        help_text=Help(
            f"The request originates on the Oxidized host. Supported schemes: {schemes}. "
            "Non-loopback cleartext HTTP requires explicit opt-in."
        ),
        elements={
            "url": DictElement(
                parameter_form=String(
                    title=Title("URL"),
                    prefill=DefaultValue(default_url),
                    custom_validate=(
                        LengthInRange(min_value=1, max_value=4096),
                        MatchRegex(
                            regex=pattern,
                            error_msg=Message("Enter a supported absolute URL."),
                        ),
                    ),
                ),
                required=True,
            ),
            "timeout_seconds": DictElement(
                parameter_form=Integer(
                    title=Title("Request timeout"),
                    unit_symbol="s",
                    prefill=DefaultValue(10),
                    custom_validate=(NumberInRange(min_value=1, max_value=120),),
                ),
                required=True,
            ),
            "max_response_bytes": DictElement(
                parameter_form=Integer(
                    title=Title("Maximum response size"),
                    unit_symbol="bytes",
                    prefill=DefaultValue(4 * 1024 * 1024),
                    custom_validate=(
                        NumberInRange(min_value=1024, max_value=64 * 1024 * 1024),
                    ),
                ),
                required=True,
            ),
            "ca_file": DictElement(
                parameter_form=_absolute_path("Custom CA bundle"),
                required=False,
            ),
            "allow_insecure_http": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Allow non-loopback cleartext HTTP"),
                    label=Label("Explicitly permit an unencrypted HTTP connection"),
                    prefill=DefaultValue(False),
                ),
                required=True,
            ),
            "auth": DictElement(
                parameter_form=_authentication(),
                required=True,
            ),
        },
    )


def _group_mapping() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Oxidized group mapping"),
        elements=(
            CascadingSingleChoiceElement(
                name="ungrouped",
                title=Title("Ungrouped/default nodes"),
                parameter_form=FixedValue(value=None),
            ),
            CascadingSingleChoiceElement(
                name="named",
                title=Title("Named Oxidized group"),
                parameter_form=String(
                    title=Title("Group name"),
                    custom_validate=(LengthInRange(min_value=1, max_value=255),),
                ),
            ),
            CascadingSingleChoiceElement(
                name="wildcard",
                title=Title("Fallback for all other groups"),
                parameter_form=FixedValue(value=None),
            ),
        ),
        prefill=DefaultValue("named"),
    )


def _repository() -> Dictionary:
    return Dictionary(
        title=Title("Oxidized Git repository"),
        elements={
            "id": DictElement(
                parameter_form=String(
                    title=Title("Repository ID"),
                    custom_validate=(
                        LengthInRange(min_value=1, max_value=128),
                        MatchRegex(
                            regex=r"^[A-Za-z0-9_.-]+$",
                            error_msg=Message(
                                "Use only letters, digits, dots, underscores, and hyphens."
                            ),
                        ),
                    ),
                ),
                required=True,
            ),
            "path": DictElement(
                parameter_form=_absolute_path("Local Git repository path"),
                required=True,
            ),
            "groups": DictElement(
                parameter_form=List(
                    title=Title("Groups stored in this repository"),
                    element_template=_group_mapping(),
                    add_element_label=Label("Add group mapping"),
                    no_element_label=Label("No group mappings configured"),
                ),
                required=True,
            ),
            "single_repo": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Single repository with group directories"),
                    label=Label("Use group/name paths for grouped nodes"),
                    prefill=DefaultValue(True),
                ),
                required=True,
            ),
            "remote": DictElement(
                parameter_form=String(
                    title=Title("Git remote"),
                    prefill=DefaultValue("origin"),
                    custom_validate=(LengthInRange(min_value=1, max_value=255),),
                ),
                required=True,
            ),
            "branch": DictElement(
                parameter_form=String(
                    title=Title("Remote branch"),
                    help_text=Help(
                        "Leave this unset to use the repository's symbolic HEAD branch."
                    ),
                    custom_validate=(LengthInRange(min_value=1, max_value=1024),),
                ),
                required=False,
            ),
            "command_timeout_seconds": DictElement(
                parameter_form=Integer(
                    title=Title("Git command timeout"),
                    unit_symbol="s",
                    prefill=DefaultValue(30),
                    custom_validate=(NumberInRange(min_value=1, max_value=300),),
                ),
                required=True,
            ),
            "fsck_timeout_seconds": DictElement(
                parameter_form=Integer(
                    title=Title("Git fsck timeout"),
                    unit_symbol="s",
                    prefill=DefaultValue(120),
                    custom_validate=(NumberInRange(min_value=1, max_value=3600),),
                ),
                required=True,
            ),
        },
    )


def _group_key(value: object) -> str:
    if isinstance(value, (tuple, list)) and value:
        mode = str(value[0])
        payload = value[1] if len(value) > 1 else None
        return f"{mode}:{payload or ''}"
    return str(value)


def _validate_repositories(value: Sequence[Mapping[str, object]]) -> None:
    if not value:
        raise ValidationError(Message("Configure at least one Git repository."))
    identifiers: list[str] = []
    wildcard_count = 0
    for repository in value:
        identifier = str(repository.get("id", ""))
        identifiers.append(identifier)
        groups = repository.get("groups", [])
        if (
            not isinstance(groups, Sequence)
            or isinstance(groups, (str, bytes))
            or not groups
        ):
            raise ValidationError(
                Message(f"Repository {identifier or '<unnamed>'} needs a group mapping.")
            )
        keys = [_group_key(group) for group in groups]
        if len(set(keys)) != len(keys):
            raise ValidationError(
                Message(f"Repository {identifier} contains duplicate group mappings.")
            )
        wildcard_count += sum(key.startswith("wildcard:") for key in keys)
    if len(set(identifiers)) != len(identifiers):
        raise ValidationError(Message("Repository IDs must be unique."))
    if wildcard_count > 1:
        raise ValidationError(
            Message("Only one repository may define the wildcard group mapping.")
        )


def _validate_policy(value: Mapping[str, object]) -> None:
    warning = float(value.get("collection_warning_age_seconds", 0))
    critical = float(value.get("collection_critical_age_seconds", 0))
    if critical <= warning:
        raise ValidationError(
            Message("Critical collection age must be greater than warning age.")
        )


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Oxidized backup verification"),
        help_text=Help(
            "Apply this rule only to the Linux host running Oxidized. The existing "
            "Checkmk-generated Oxidized JSON remains the sole device inventory."
        ),
        elements={
            "deployment": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment and execution"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="cached",
                            title=Title("Deploy and cache output"),
                            parameter_form=TimeSpan(
                                title=Title("Execution interval"),
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                    TimeMagnitude.SECOND,
                                ),
                                prefill=DefaultValue(300.0),
                                custom_validate=(
                                    NumberInRange(min_value=60, max_value=86400),
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy and run synchronously"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("cached"),
                ),
                required=True,
            ),
            "inventory": DictElement(
                parameter_form=_endpoint(
                    "Existing Checkmk Oxidized export",
                    "https://checkmk.example.invalid/site/open/oxidized.json",
                    allow_file=True,
                ),
                required=True,
            ),
            "oxidized": DictElement(
                parameter_form=_endpoint(
                    "Oxidized node API",
                    "http://127.0.0.1:8888/nodes.json",
                    allow_file=False,
                ),
                required=True,
            ),
            "state": DictElement(
                parameter_form=Dictionary(
                    title=Title("Persistent state"),
                    elements={
                        "hook_state_file": DictElement(
                            parameter_form=_absolute_path(
                                "Oxidized hook state file",
                                "/var/lib/oxidized/oxidized_backup/hook-state.json",
                            ),
                            required=True,
                        ),
                        "monitor_state_file": DictElement(
                            parameter_form=_absolute_path(
                                "Checkmk monitor state file",
                                "/var/lib/check_mk_agent/oxidized_backup/monitor-state.json",
                            ),
                            required=True,
                        ),
                    },
                ),
                required=True,
            ),
            "git": DictElement(
                parameter_form=Dictionary(
                    title=Title("Oxidized Git storage"),
                    help_text=Help(
                        "Git commands run as the configured unprivileged account and "
                        "never modify the repository."
                    ),
                    elements={
                        "run_as_user": DictElement(
                            parameter_form=String(
                                title=Title("Oxidized service account"),
                                prefill=DefaultValue("oxidized"),
                                custom_validate=(
                                    LengthInRange(min_value=1, max_value=128),
                                    MatchRegex(
                                        regex=r"^(?!root$)[A-Za-z_][A-Za-z0-9_.-]*[$]?$",
                                        error_msg=Message(
                                            "Enter a valid unprivileged account name."
                                        ),
                                    ),
                                ),
                            ),
                            required=True,
                        ),
                        "git_binary": DictElement(
                            parameter_form=_absolute_path(
                                "Git executable",
                                "/usr/bin/git",
                            ),
                            required=True,
                        ),
                        "repositories": DictElement(
                            parameter_form=List(
                                title=Title("Repositories"),
                                element_template=_repository(),
                                add_element_label=Label("Add Git repository"),
                                no_element_label=Label("No repositories configured"),
                                custom_validate=(_validate_repositories,),
                            ),
                            required=True,
                        ),
                    },
                ),
                required=True,
            ),
            "policy": DictElement(
                parameter_form=Dictionary(
                    title=Title("Monitoring policy"),
                    custom_validate=(_validate_policy,),
                    elements={
                        "collection_warning_age_seconds": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Collection warning age"),
                                displayed_magnitudes=(
                                    TimeMagnitude.DAY,
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(7200.0),
                            ),
                            required=True,
                        ),
                        "collection_critical_age_seconds": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Collection critical age"),
                                displayed_magnitudes=(
                                    TimeMagnitude.DAY,
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(14400.0),
                            ),
                            required=True,
                        ),
                        "remote_sync_grace_seconds": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Remote synchronization grace period"),
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                    TimeMagnitude.SECOND,
                                ),
                                prefill=DefaultValue(300.0),
                            ),
                            required=True,
                        ),
                        "remote_verification_max_age_seconds": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Maximum remote verification age"),
                                displayed_magnitudes=(
                                    TimeMagnitude.DAY,
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(3600.0),
                            ),
                            required=True,
                        ),
                        "fsck_interval_seconds": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Git integrity-check interval"),
                                displayed_magnitudes=(
                                    TimeMagnitude.DAY,
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(3600.0),
                                custom_validate=(
                                    NumberInRange(min_value=300, max_value=604800),
                                ),
                            ),
                            required=True,
                        ),
                        "orphan_state": DictElement(
                            parameter_form=SingleChoice(
                                title=Title("State for orphaned Oxidized nodes"),
                                elements=(
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(
                                        name="warn",
                                        title=Title("WARN"),
                                    ),
                                    SingleChoiceElement(
                                        name="crit",
                                        title=Title("CRIT"),
                                    ),
                                ),
                                prefill=DefaultValue("warn"),
                            ),
                            required=True,
                        ),
                    },
                ),
                required=True,
            ),
        },
    )


rule_spec_oxidized_backup_bakery = AgentConfig(
    name="oxidized_backup",
    title=Title("Oxidized backup verification"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
)
