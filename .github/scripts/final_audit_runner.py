#!/usr/bin/env python3
"""Publish the exact, checksum-pinned final repository audit tree.

The runner is temporary bootstrap code executed from the trusted default branch.
It treats the staging branch as untrusted transport: every accepted path, archive,
patch, byte count, and resulting repository file is verified before any code from
the reconstructed tree is executed. Publication uses a force-with-lease update
against the exact reviewed staging SHA.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request

REPOSITORY = "DanielDietz-de/Checkmk-Checks"
BRANCH = "agent/final-repository-completion-audit"
EXPECTED_PREVIOUS_MASTER = "ebcfaa1c36b7e33c304ec3357f56c85eeb6f0c63"
EXPECTED_MASTER_PATHS = (
    ".github/scripts/final_audit_runner.py",
    ".github/workflows/final-audit-runner.yml",
)
EXPECTED_AUDIT_BASE = "ff1129c75c59f79ebec3d1fb61506a5d76c9ca4b"
EXPECTED_STAGING_SHA = "a63b0b2b0b495d316eb506c47cd514f627e746e2"
EXPECTED_BASE64_SHA256 = "989206ae474beb1ef1756095a617e031d2df99394c26dfd1775c40a5c217b0e6"
EXPECTED_GZIP_SHA256 = "a474d18b5cf6084fe4dbb8b1bfe90472ca6cba2dc0a9d717734c3629b37717cc"
EXPECTED_PATCH_SHA256 = "0a02b2c64eaed2c00dac46db6b72c5156216afbd50b4224bee8ee7648c04f9f0"
EXPECTED_PATCH_FILES = 204
EXPECTED_ADDITIONS_BASE64_SHA256 = "04ed99e34b860d01c7fc86dddf5cd03437c85fe35d76cd56f948f561b9268257"
EXPECTED_ADDITIONS_XZ_SHA256 = "9c2f00b5c45dfe747a7873da56709f2cb7c0c7724b86c7e77db4a5e6c49e65cb"
EXPECTED_FILES = 1667
EXPECTED_MANIFEST_SHA256 = "d84a25b3b61e63ff5ab13c86bf1d78375b7fd5ced4183282a5dbf16096800cd4"

EXCLUDED_MANIFEST_PARTS = {".git", ".pytest_cache", "__pycache__"}
ALLOWED_STAGING_ROOTS = (
    ".github/final-audit-patch/",
    ".github/final-audit-payload/",
    ".github/final-audit-additions/",
)
ALLOWED_STAGING_FILE = ".github/workflows/apply-final-repository-audit.yml"


def run(*args: str, cwd: Path, capture: bool = False) -> str:
    """Run one bounded command in ``cwd`` and return captured stdout when requested."""

    completed = subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return completed.stdout.strip() if capture else ""


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 digest for ``data``."""

    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    """Abort the transaction with ``message`` when ``condition`` is false."""

    if not condition:
        raise RuntimeError(message)


def verify_master_state(repository: Path) -> str:
    """Verify the bootstrap merge is the sole change after the trusted master."""

    run("git", "fetch", "--no-tags", "origin", "master", cwd=repository)
    master_sha = run("git", "rev-parse", "origin/master", cwd=repository, capture=True)
    first_parent = run("git", "rev-parse", "origin/master^1", cwd=repository, capture=True)
    require(
        first_parent == EXPECTED_PREVIOUS_MASTER,
        f"master first parent {first_parent} is not {EXPECTED_PREVIOUS_MASTER}",
    )
    changed = run(
        "git",
        "diff",
        "--name-only",
        EXPECTED_PREVIOUS_MASTER,
        master_sha,
        cwd=repository,
        capture=True,
    ).splitlines()
    require(
        tuple(sorted(changed)) == tuple(sorted(EXPECTED_MASTER_PATHS)),
        f"unexpected master bootstrap paths: {changed}",
    )
    return master_sha


def verify_staging_state(repository: Path) -> None:
    """Verify the checkout is the exact reviewed transport commit and path set."""

    actual = run("git", "rev-parse", "HEAD", cwd=repository, capture=True)
    require(actual == EXPECTED_STAGING_SHA, f"staging SHA moved to {actual}")
    changed = run(
        "git",
        "diff",
        "--name-only",
        EXPECTED_AUDIT_BASE,
        "HEAD",
        cwd=repository,
        capture=True,
    ).splitlines()
    for raw in changed:
        path = PurePosixPath(raw)
        require(not path.is_absolute() and ".." not in path.parts, f"unsafe staging path: {raw!r}")
        require(
            raw == ALLOWED_STAGING_FILE or raw.startswith(ALLOWED_STAGING_ROOTS),
            f"non-payload staging path: {raw!r}",
        )


def reconstruct_audit_patch(repository: Path, temporary: Path) -> Path:
    """Verify and decode the legacy 204-file audit patch into ``temporary``."""

    chunks = sorted((repository / ".github/final-audit-patch").glob("chunk*.b64"))
    require(len(chunks) == 9, f"expected 9 patch chunks, found {len(chunks)}")
    encoded = b"".join(path.read_bytes() for path in chunks)
    require(sha256_bytes(encoded) == EXPECTED_BASE64_SHA256, "audit base64 digest mismatch")
    compressed = base64.b64decode(encoded, validate=True)
    require(sha256_bytes(compressed) == EXPECTED_GZIP_SHA256, "audit gzip digest mismatch")

    import gzip

    patch = gzip.decompress(compressed)
    require(sha256_bytes(patch) == EXPECTED_PATCH_SHA256, "audit patch digest mismatch")
    patch_path = temporary / "final-audit.patch"
    patch_path.write_bytes(patch)

    paths: list[str] = []
    for line in patch.decode("utf-8").splitlines():
        if not line.startswith("+++ source/"):
            continue
        raw = line.split("\t", 1)[0][len("+++ source/") :]
        path = PurePosixPath(raw)
        require(not path.is_absolute() and ".." not in path.parts, f"unsafe patch path: {raw!r}")
        require(
            not raw.startswith(".github/final-audit-")
            and not raw.startswith(".github/workflows/final-audit-"),
            f"patch contains bootstrap path: {raw!r}",
        )
        paths.append(raw)
    require(
        len(paths) == EXPECTED_PATCH_FILES and len(set(paths)) == EXPECTED_PATCH_FILES,
        f"expected {EXPECTED_PATCH_FILES} unique patch paths; got {len(paths)} / {len(set(paths))}",
    )
    return patch_path


def extract_additions(repository: Path, temporary: Path) -> Path:
    """Verify and safely extract the full-tree documentation additions archive."""

    source = repository / ".github/final-audit-additions/additions.b64"
    encoded = source.read_bytes()
    require(
        sha256_bytes(encoded) == EXPECTED_ADDITIONS_BASE64_SHA256,
        "additions base64 digest mismatch",
    )
    compressed = base64.b64decode(encoded, validate=True)
    require(sha256_bytes(compressed) == EXPECTED_ADDITIONS_XZ_SHA256, "additions xz digest mismatch")
    archive_path = temporary / "audit-additions.tar.xz"
    archive_path.write_bytes(compressed)
    target = temporary / "audit-additions"
    target.mkdir()

    total = 0
    with tarfile.open(archive_path, mode="r:xz") as archive:
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and ".." not in path.parts, f"unsafe archive path: {member.name!r}")
            require(
                member.name in {"runtime", "payload"}
                or member.name.startswith(("runtime/", "payload/")),
                f"unexpected additions member: {member.name!r}",
            )
            require(
                not (member.issym() or member.islnk() or member.isdev()),
                f"unsupported additions member type: {member.name!r}",
            )
            total += member.size
        require(total <<BË ôˆdÈ8Ð ¢6‡WF–Âç&×G&VR‡&W÷6—F÷'’ò"æv—F‡V"öf–æÂÖVF—BÖFF—F–öç2"¢f÷"&VÆF—fR–â€¢"æv—F‡V"öf–æÂÖVF—B×G&–vvW""À¢"æv—F‡V"÷v÷&¶fÆ÷w2öf–æÂÖVF—BÖ÷&6†W7G&F÷"ç–ÖÂ"À¢"æv—F‡V"÷67&—G2öf–æÅöVF—E÷'VææW"ç’"À¢"æv—F‡V"÷v÷&¶fÆ÷w2öf–æÂÖVF—B×'VææW"ç–ÖÂ"À¢“ ¢‡&W÷6—F÷'’ò&VÆF—fR’çVæÆ–æ²†Ö—76–æuöö³ÕG'VR  ¦FVbfW&–g•÷6÷W&6UöÖæ–fW7B‡&W÷6—F÷'“¢F‚’ÓâæöæS ¢""%fW&–g’WfW'’f–æÂ6÷W&6R'—FRæBW†V7WF&ÆRÖöFRv–ç7BF†R&Wf–WvVBÖæ–fW7Bâ""  ¢VçG&–W3¢Æ—7E·7G%ÒÒµÐ¢f÷"F‚–â6÷'FVB‡&W÷6—F÷'’ç&vÆö"‚"¢"’“ ¢&VÆF—fRÒF‚ç&VÆF—fU÷Fò‡&W÷6—F÷'’¢–bç’‡'B–âU„4ÅTDTEôÔä”dU5Eõ%E2f÷"'B–â&VÆF—fRç'G2’÷"æ÷BF‚æ—5öf–ÆR‚“ ¢6öçF–çVP¢ÖöFRÒ#sSR"–bF‚ç7FB‚’ç7EöÖöFRb7FBå5ô•…U5"VÇ6R#cCB ¢VçG&–W2æVæB†b'¶ÖöFWÒ·6†#Seö'—FW2‡F‚ç&VEö'—FW2‚’—Ò·&VÆF—fRæ5÷÷6—‚‚—Ò"¢F–vW7BÒ6†#Seö'—FW2‚‚%Æâ"æ¦ö–â†VçG&–W2’²%Æâ"’æVæ6öFR‚’¢&WV—&R€¢ÆVâ†VçG&–W2’ÓÒU…T5DTEôd”ÄU2æBF–vW7BÓÒU…T5DTEôÔä”dU5Eõ4„#SbÀ¢b'6÷W&6RÖæ–fW7BÖ—6ÖF6ƒ¢f–ÆW3×¶ÆVâ†VçG&–W2—Ò6†#Sc×¶F–vW7GÒ"À¢¢&–çB†b%fW&–f–VBW†7B6÷W&6RÖæ–fW7C¢¶ÆVâ†VçG&–W2—Òf–ÆW2Â6†#Sc×¶F–vW7GÒ"  ¦FVbfÆ–FFU÷G&VR‡&W÷6—F÷'“¢F‚’ÓâæöæS ¢""%'VâF†R6ö×ÆWFR&W÷6—F÷'’Â6V7W&—G’ÂFö7VÖVçFF–öâÂFW7BÂæBÔµvFW2â""  ¢6öÖÖæG2Ò€¢‡7—2æW†V7WF&ÆRÂ'FööÇ2ö6’÷–å÷7WÇ•ö6†–âç’"Â"ÒÖ6†V6²"’À¢‡7—2æW†V7WF&ÆRÂ'FööÇ2ö6’öæ÷&ÖÆ—¦U÷6¶vU÷6÷W&6W2ç’"’À¢‡7—2æW†V7WF&ÆRÂ'FööÇ2ö6’ö6†V6µ÷6¶vUö6öÆÆ—6–öç2ç’"’À¢‡7—2æW†V7WF&ÆRÂ'FööÇ2ö6’ö6†V6µ÷&W÷6—F÷'•÷VÆ—G’ç’"’À¢‡7—2æW†V7WF&ÆRÂ'FööÇ2ö6’÷7–æ5÷&W÷6—F÷'•öf7G2ç’"’À¢‡7—2æW†V7WF&ÆRÂ'FööÇ2ö6’÷7–æ5÷6¶vUöÖWFFFç’"’À¢‡7—2æW†V7WF&ÆRÂ'FööÇ2ö6’övVæW&FU÷6¶vU÷&VfW&Væ6Rç’"’À¢‡7—2æW†V7WF&ÆRÂ'FööÇ2ö6’öÖævUöÖöGVÆUöFö77G&–æw2ç’"’À¢‡7—2æW†V7WF&ÆRÂ'FööÇ2ö6’ö6†V6µ÷—F†öå÷7–çF‚ç’"’À¢€¢7—2æW†V7WF&ÆRÀ¢'FööÇ2ö6’ögVÆÅ÷&W÷6—F÷'•öVF—Bç’"À¢"ÒÖf–ÂÖöâ"À¢&Æ÷r"À¢"ÒÖ÷WGWB"À¢"÷F×÷&W÷6—F÷'’ÖVF—Bæ§6öâ"À¢’À¢‡7—2æW†V7WF&ÆRÂ"ÖÒ"Â'Væ—GFW7B"Â&F—66÷fW""Â"×2"Â'FW7G2"Â"×"Â'FW7Eö6•ò¢ç’"Â"×b"’À¢‚'—FW7B"Â"×"Â"æv—F‡V"÷FW7G2"’À¢‚&&6‚"Â"ÖÆ2"Â'—FW7B×¢÷FW7G2"’À¢€¢7—2æW†V7WF&ÆRÀ¢"æv—F‡V"÷67&—G2ö'V–ÆE÷&W÷6—F÷'•öÖ·2ç’"À¢"Ò×&W÷6—F÷'’"À¢"â"À¢"ÒÖ÷WGWB"À¢"÷F×÷&W÷6—F÷'’ÖÖ·2"À¢"Ò×6¶vVB×fW'6–öâ"À¢#"ãRã’"À¢’À¢¢f÷"6öÖÖæB–â6öÖÖæG3 ¢'Vâ‚¦6öÖÖæBÂ7vC×&W÷6—F÷'’  ¦FVbV&Æ—6…÷G&VR‡&W÷6—F÷'“¢F‚ÂÖ7FW%÷6†¢7G"’Óâ7G# ¢""$7&VFRæBf÷&6R×v—F‚ÖÆV6RV&Æ—6‚öæR6ÆVâ6öÖÖ—B&VçFVBFòÖ7FW%÷6†â""  ¢'Vâ‚&v—B"Â&6öæf–r"Â'W6W"ææÖR"Â&v—F‡V"Ö7F–öç5¶&÷EÒ"Â7vC×&W÷6—F÷'’¢'Vâ€¢&v—B"À¢&6öæf–r"À¢'W6W"æVÖ–Â"À¢#Cƒ“ƒ#ƒ"¶v—F‡V"Ö7F–öç5¶&÷EÔW6W'2ææ÷&WÇ’æv—F‡V"æ6öÒ"À¢7vC×&W÷6—F÷'’À¢¢'Vâ‚&v—B"Â&FB"Â"ÒÖÆÂ"Â7vC×&W÷6—F÷'’¢G&VRÒ'Vâ‚&v—B"Â'w&—FR×G&VR"Â7vC×&W÷6—F÷'’Â6GW&SÕG'VR¢6ö×ÆWFVBÒ7V'&ö6W72ç'Vâ€¢‚&v—B"Â&6öÖÖ—B×G&VR"ÂG&VRÂ"×"ÂÖ7FW%÷6†’À¢7vC×&W÷6—F÷'’À¢–çWCÒ&VF—C¢6ö×ÆWFR&W÷6—F÷'’fÆ–FF–öâæB†&FVæ–æuÆâ"À¢FW‡CÕG'VRÀ¢6†V6³ÕG'VRÀ¢7FF÷WC×7V'&ö6W72å•RÀ¢¢6öÖÖ—BÒ6ö×ÆWFVBç7FF÷WBç7G&—‚¢'Vâ€¢&v—B"À¢'W6‚"À¢b"ÒÖf÷&6R×v—F‚ÖÆV6S×&Vg2ö†VG2÷´%$ä4‡Ó§´U…T5DTEõ5Dt”äuõ4„Ò"À¢&÷&–v–â"À¢b'¶6öÖÖ—GÓ§&Vg2ö†VG2÷´%$ä4‡Ò"À¢7vC×&W÷6—F÷'’À¢¢&WGW&â6öÖÖ—@  ¦FVbF—7F6…÷v÷&¶fÆ÷r‡v÷&¶fÆ÷s¢7G"ÂFö¶Vã¢7G"’ÓâæöæS ¢""$F—7F6‚öæRWF†÷&—FF—fRv÷&¶fÆ÷rv–ç7BF†Rf–æÂVF—B'&æ6‚â""  ¢W&ÂÒb&‡GG3¢òö’æv—F‡V"æ6öÒ÷&W÷2÷µ$Uõ4•Dõ%—Òö7F–öç2÷v÷&¶fÆ÷w2÷·v÷&¶fÆ÷wÒöF—7F6†W2 ¢–ÆöBÒ†bw·²'&Vb#¢'´%$ä4‡Ò'×Òr’æVæ6öFR‚¢&WVW7BÒW&ÆÆ–"ç&WVW7Bå&WVW7B€¢W&ÂÀ¢FF×–ÆöBÀ¢ÖWF†öCÒ%õ5B"À¢†VFW'3×°¢$66WB#¢&Æ–6F–öâ÷fæBæv—F‡V"¶§6öâ"À¢$WF†÷&—¦F–öâ#¢b$&V&W"·Fö¶VçÒ"À¢%‚Ôv—D‡V"Ô’ÕfW'6–öâ#¢###"ÓÓ#‚"À¢$6öçFVçBÕG—R#¢&Æ–6F–öâö§6öâ"À¢ÒÀ¢¢v—F‚W&ÆÆ–"ç&WVW7BçW&Æ÷Vâ‡&WVW7BÂF–ÖV÷WCÓ3’2&W7öç6S ¢&WV—&R‡&W7öç6Rç7FGW2ÓÒ#BÂb'v÷&¶fÆ÷rF—7F6‚&WGW&æVB…EE·&W7öç6Rç7FGW7Ò"  ¦FVb'6Uö&w2‚’Óâ&w'6RäæÖW76S ¢""%'6RF†R&W÷6—F÷'’F‚æBV&Æ–6F–öâ6öçG&öÇ2â""  ¢'6W"Ò&w'6Rä&wVÖVçE'6W"‚¢'6W"æFEö&wVÖVçB‚"Ò×&W÷6—F÷'’"ÂG—SÕF‚Â&WV—&VCÕG'VR¢'6W"æFEö&wVÖVçB‚"Ò×6¶—×V&Æ—6‚"Â7F–öãÒ'7F÷&U÷G'VR"¢&WGW&â'6W"ç'6Uö&w2‚  ¦FVbÖ–â‚’Óâ–çC ¢""$W†V7WFRF†Rf–ÂÖ6Æ÷6VB&V6öç7G'V7F–öâÂfÆ–FF–öâÂæBV&Æ–6F–öâG&ç67F–öââ""  ¢&w2Ò'6Uö&w2‚¢&W÷6—F÷'’Ò&w2ç&W÷6—F÷'’ç&W6öÇfR‚¢&WV—&R‚‡&W÷6—F÷'’ò"æv—B"’æW†—7G2‚’Âb&æ÷Bv—B6†V6¶÷WC¢·&W÷6—F÷'—Ò"¢Ö7FW%÷6†ÒfW&–g•öÖ7FW%÷7FFR‡&W÷6—F÷'’¢fW&–g•÷7Fv–æu÷7FFR‡&W÷6—F÷'’ ¢FV×÷&'’ÒF‚‚"÷F×öf–æÂÖVF—B×'VææW""¢6‡WF–Âç&×G&VR‡FV×÷&'’Â–væ÷&UöW'&÷'3ÕG'VR¢FV×÷&'’æÖ¶F—"‚¢F6‚Ò&V6öç7G'V7EöVF—E÷F6‚‡&W÷6—F÷'’ÂFV×÷&'’¢FF—F–öç2ÒW‡G&7EöFF—F–öç2‡&W÷6—F÷'’ÂFV×÷&'’¢&V6öç7G'V7E÷G&VR‡&W÷6—F÷'’ÂF6‚ÂFF—F–öç2¢fW&–g•÷6÷W&6UöÖæ–fW7B‡&W÷6—F÷'’¢fÆ–FFU÷G&VR‡&W÷6—F÷'’ ¢–b&w2ç6¶—÷V&Æ—6ƒ ¢&–çB‚%fÆ–FF–öâ6ö×ÆWFS²V&Æ–6F–öâ6¶—VBâ"¢&WGW&â  ¢6öÖÖ—BÒV&Æ—6…÷G&VR‡&W÷6—F÷'’ÂÖ7FW%÷6†¢Fö¶VâÒ÷2æVçf—&öâævWB‚$t•D…T%õDô´Tâ"Â""¢&WV—&R†&ööÂ‡Fö¶Vâ’Â$t•D…T%õDô´Tâ—2&WV—&VBf÷"W†7BÖ†VBv÷&¶fÆ÷rF—7F6‚"¢f÷"v÷&¶fÆ÷r–â‚'&W÷6—F÷'’ÖwV&Bç–ÖÂ"Â'&W÷6—F÷'’ÖÖ·Ö6’ç–ÖÂ"“ ¢F—7F6…÷v÷&¶fÆ÷r‡v÷&¶fÆ÷rÂFö¶Vâ¢÷WGWBÒ÷2æVçf—&öâævWB‚$t•D…T%ôõUEUB"¢–b÷WGWC ¢v—F‚F‚†÷WGWB’æ÷Vâ‚&"ÂVæ6öF–æsÒ'WFbÓ‚"’2†æFÆS ¢†æFÆRçw&—FR†b&f–æÅ÷6†×¶6öÖÖ—GÕÆâ"¢&–çB†b%V&Æ—6†VB6ÆVâVF—B6öÖÖ—B¶6öÖÖ—GÒ"¢&WGW&â   ¦–bõöæÖUõòÓÒ%õöÖ–åõò# ¢G'“ ¢&—6R7—7FVÔW†—B†Ö–â‚’¢W†6WB„õ4W'&÷"Â'VçF–ÖTW'&÷"Â7V'&ö6W72ä6ÆÆVE&ö6W74W'&÷"’2W†3 ¢&–çB†b&f–æÂVF—B'VææW"f–ÆVC¢¶W†7Ò"Âf–ÆS×7—2ç7FFW'"¢&—6R7—7FVÔW†—Bƒ’g&öÒW†0 