#!/usr/bin/env python3
"""Generate the active repository MKP index from canonical top-level manifests."""

from __future__ import annotations

import ast
import json
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parent


def main() -> None:
    output: list[dict[str, str]] = []
    for info_path in sorted(REPOSITORY.glob("*/src/info")):
        package_dir = info_path.parent.parent
        data = ast.literal_eval(info_path.read_text(encoding="utf-8"))
        name = str(data["name"])
        version = str(data["version"])
        output.append(
            {
                "title": str(data["title"]),
                "name": name,
                "description": str(data.get("description", "")),
                "version": version,
                "version_required": str(data["version.min_required"]),
                "mkp": f"{package_dir.name}/{name}-{version}.mkp",
            }
        )
        print(f"{package_dir.name}: {data['title']}, {version}")

    output.sort(key=lambda item: (item["name"].casefold(), item["mkp"]))
    (REPOSITORY / "mkp_index.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Indexed {len(output)} active packages")


if __name__ == "__main__":
    main()
