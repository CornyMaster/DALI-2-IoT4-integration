"""Deploy bundled Switch Manager blueprints into the HA config when present.

Switch Manager (HACS) reads blueprints from ``config/blueprints/switch_manager``.
The integration ships its blueprint + image and copies them there so DALI-2
push-button couplers can be mapped without manual file handling.

Update safety via a hash history (``known_hashes.json``): each shipped file has
a list of every SHA-256 it ever had. Auto-deploy only replaces a target whose
current hash is a known old bundled version (or that is missing) — a
user-edited file has an unknown hash and is kept. The manual button passes
``force`` to overwrite regardless.
"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
from pathlib import Path

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

SOURCE_DIR = Path(__file__).parent / "blueprints"
HASHES_FILE = SOURCE_DIR / "known_hashes.json"
TARGET_REL = "blueprints/switch_manager"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _deploy(config_dir: str, force: bool) -> int:
    """Copy bundled blueprints into the Switch Manager folder. Executor-only."""
    cfg = Path(config_dir)
    # Switch Manager installed? (HACS custom component). Its user blueprints go
    # to config/blueprints/switch_manager (created here if missing).
    if not (cfg / "custom_components" / "switch_manager").is_dir():
        return -1
    target = cfg / TARGET_REL
    target.mkdir(parents=True, exist_ok=True)
    try:
        known = json.loads(HASHES_FILE.read_text()) if HASHES_FILE.exists() else {}
    except (OSError, ValueError):
        known = {}
    copied = 0
    for src in SOURCE_DIR.glob("*"):
        if src.suffix not in (".yaml", ".png", ".svg"):
            continue
        dst = target / src.name
        if dst.exists() and not force:
            dst_hash = _sha256(dst)
            if dst_hash == _sha256(src):
                continue  # already current
            if dst_hash not in known.get(src.name, []):
                continue  # user-modified: keep it
            # else: a previous bundled version -> safe to update
        shutil.copy2(src, dst)
        copied += 1
    return copied


async def async_deploy_switch_manager_blueprints(
    hass: HomeAssistant, force: bool = False
) -> int:
    """Deploy blueprints; returns copied count, or -1 if SM is not installed."""
    n = await hass.async_add_executor_job(_deploy, hass.config.config_dir, force)
    if n > 0:
        _LOGGER.info("Deployed %d Switch Manager blueprint file(s)", n)
    return n
