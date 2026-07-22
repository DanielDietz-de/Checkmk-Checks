#!/usr/bin/env python3
"""Apply the final nested-action-path fix to the supply-chain pinner."""

from pathlib import Path

PATH = Path("tools/ci/pin_supply_chain_corrected.py")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if text.count(old) != 1:
        raise SystemExit(f"Could not patch {label}: expected exactly one match")
    return text.replace(old, new, 1)


text = PATH.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''ACTION_RE = re.compile(\n    r"(?P<prefix>\\buses:\\s*)(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"\n    r"@(?P<ref>[^\\s#]+)(?P<suffix>\\s*(?:#.*)?)$"\n)\n''',
    '''ACTION_RE = re.compile(\n    r"(?P<prefix>\\buses:\\s*)"\n    r"(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"\n    r"(?P<action_path>(?:/[A-Za-z0-9_.-]+)*)"\n    r"@(?P<ref>[^\\s#]+)(?P<suffix>\\s*(?:#.*)?)$"\n)\n''',
    "action regex",
)
text = replace_once(
    text,
    '''            repo = action_match.group("repo")\n            ref = action_match.group("ref")\n            source_ref = source_comment(action_match.group("suffix"), ref)\n            sha = ref if FULL_SHA_RE.fullmatch(ref) else resolve_action(repo, ref)\n            action_locks[f"{repo}@{source_ref}"] = {\n                "repository": repo,\n                "source_ref": source_ref,\n                "commit": sha,\n            }\n            body = (\n                body[: action_match.start()]\n                + action_match.group("prefix")\n                + repo\n                + "@"\n                + sha\n                + f" # {source_ref}"\n            )\n''',
    '''            repo = action_match.group("repo")\n            action_path = action_match.group("action_path")\n            action_id = repo + action_path\n            ref = action_match.group("ref")\n            source_ref = source_comment(action_match.group("suffix"), ref)\n            sha = ref if FULL_SHA_RE.fullmatch(ref) else resolve_action(repo, ref)\n            action_locks[f"{action_id}@{source_ref}"] = {\n                "repository": repo,\n                "action_path": action_path,\n                "source_ref": source_ref,\n                "commit": sha,\n            }\n            body = (\n                body[: action_match.start()]\n                + action_match.group("prefix")\n                + action_id\n                + "@"\n                + sha\n                + f" # {source_ref}"\n            )\n''',
    "action path handling",
)
text = replace_once(
    text,
    '''                    f"{path.relative_to(root)}:{number}: mutable action "\n                    f"{match.group('repo')}@{match.group('ref')}"\n''',
    '''                    f"{path.relative_to(root)}:{number}: mutable action "\n                    f"{match.group('repo')}{match.group('action_path')}@"\n                    f"{match.group('ref')}"\n''',
    "mutable action message",
)
PATH.write_text(text, encoding="utf-8")
print(f"Finalized {PATH}")
