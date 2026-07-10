#!/usr/bin/env python3
"""Inject Checkmk compatibility badges into each plugin README.

Only "Checkmk min" and "packaged" are rendered. No maximum-version badge and
no `version.usable_until` is written into the info files — a fixed maximum is a
false compatibility promise (plugins built for 2.4 also run on 2.5) and can
block Exchange upload / installation on newer patches."""
import ast
import re
import urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parent
START = "<!-- compatibility-badges:start -->"
END = "<!-- compatibility-badges:end -->"


def badge(label, message, color):
    label_e = urllib.parse.quote(label)
    msg_e = urllib.parse.quote(message)
    return f"![{label}](https://img.shields.io/badge/{label_e}-{msg_e}-{color})"


def build_block(info):
    min_ver = info.get("version.min_required") or "n/a"
    packaged = info.get("version.packaged") or "n/a"
    badges = " ".join([
        badge("Checkmk min", min_ver, "2f4f4f"),
        badge("packaged", packaged, "blue"),
    ])
    return f"{START}\n{badges}\n{END}"


def inject(readme_text, block, title):
    if START in readme_text and END in readme_text:
        return re.sub(
            re.escape(START) + r".*?" + re.escape(END),
            block,
            readme_text,
            count=1,
            flags=re.DOTALL,
        )
    # Try to inject after first H1
    m = re.search(r"^(#\s+.+?)\n", readme_text, flags=re.MULTILINE)
    if m:
        idx = m.end()
        return readme_text[:idx] + "\n" + block + "\n" + readme_text[idx:]
    # No H1: prepend with title
    return f"# {title}\n\n{block}\n\n{readme_text}"


def create(info, block):
    title = info.get("title", info.get("name", "Plugin"))
    desc = info.get("description", "").rstrip()
    return f"# {title}\n\n{block}\n\n{desc}\n"


def main():
    infos = sorted(REPO.glob("*/src/info"))
    created = []
    updated = []
    for info_path in infos:
        plugin_dir = info_path.parent.parent
        try:
            info = ast.literal_eval(info_path.read_text())
        except Exception as e:
            print(f"SKIP {plugin_dir.name}: {e}")
            continue
        readme = plugin_dir / "README.md"
        block = build_block(info)
        title = info.get("title", info.get("name", plugin_dir.name))
        if readme.exists():
            old = readme.read_text()
            new = inject(old, block, title)
            if new != old:
                readme.write_text(new)
                updated.append(plugin_dir.name)
        else:
            readme.write_text(create(info, block))
            created.append(plugin_dir.name)
    print(f"Created {len(created)}:")
    for n in created:
        print(f"  + {n}")
    print(f"Updated {len(updated)}:")
    for n in updated:
        print(f"  ~ {n}")


if __name__ == "__main__":
    main()
