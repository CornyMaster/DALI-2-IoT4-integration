"""Deploy bundled Switch Manager blueprints into the HA config when present.

Switch Manager (HACS) reads blueprints from ``config/blueprints/switch_manager``.
The integration ships its blueprint + image and copies them there so DALI-2
push-button couplers can be mapped without manual file handling.

Update handling via a hash history (``known_hashes.json`` lists every SHA-256 a
shipped file ever had):

* missing target -> deployed;
* target equals the current bundled file -> nothing to do;
* target equals a known *older* bundled version -> safely refreshed;
* target hash is unknown (edited by the user or rewritten by Switch Manager) ->
  kept, and a **dismissible notification** is raised suggesting the force
  deploy button. That notification is gated by the bundled file's hash, so it
  only reappears after the integration ships a new blueprint version.

The force deploy button overwrites unconditionally and clears the notice.
"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
from pathlib import Path

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

SOURCE_DIR = Path(__file__).parent / "blueprints"
HASHES_FILE = SOURCE_DIR / "known_hashes.json"
TARGET_REL = "blueprints/switch_manager"
STATE_REL = ".storage/lunatone_dali2_iot4_blueprints.json"
NOTIFICATION_ID = "lunatone_dali2_iot4_blueprint_outdated"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _deploy(config_dir: str, force: bool) -> tuple[int, list[str]]:
    """Copy bundled blueprints. Returns (copied, modified_filenames).

    ``copied`` is -1 if Switch Manager is not installed. ``modified`` lists
    files kept because their hash is unknown (user/SM edited).
    """
    cfg = Path(config_dir)
    if not (cfg / "custom_components" / "switch_manager").is_dir():
        return -1, []
    target = cfg / TARGET_REL
    target.mkdir(parents=True, exist_ok=True)
    try:
        known = json.loads(HASHES_FILE.read_text()) if HASHES_FILE.exists() else {}
    except (OSError, ValueError):
        known = {}
    copied = 0
    modified: list[str] = []
    for src in SOURCE_DIR.glob("*"):
        if src.suffix not in (".yaml", ".png", ".svg"):
            continue
        dst = target / src.name
        if dst.exists() and not force:
            dst_hash = _sha256(dst)
            if dst_hash == _sha256(src):
                continue  # already current
            if dst_hash not in known.get(src.name, []):
                modified.append(src.name)  # edited/rewritten -> keep, notify
                continue
        shutil.copy2(src, dst)
        copied += 1
    return copied, modified


def _read_state(cfg: Path) -> dict:
    f = cfg / STATE_REL
    try:
        return json.loads(f.read_text()) if f.exists() else {}
    except (OSError, ValueError):
        return {}


def _gate_notification(config_dir: str, modified: list[str]) -> list[str]:
    """Return files to notify about (bundled hash changed since last notice)."""
    cfg = Path(config_dir)
    state = _read_state(cfg)
    to_notify = []
    for name in modified:
        bundled = _sha256(SOURCE_DIR / name)
        if state.get(name) != bundled:
            to_notify.append(name)
            state[name] = bundled
    if to_notify:
        try:
            (cfg / STATE_REL).write_text(json.dumps(state))
        except OSError as err:
            _LOGGER.debug("Could not persist blueprint notify state: %s", err)
    return to_notify


async def async_deploy_switch_manager_blueprints(
    hass: HomeAssistant, force: bool = False
) -> int:
    """Deploy blueprints; returns copied count, or -1 if SM is not installed.

    Raises a dismissible notification for blueprints kept because they were
    modified, but only once per shipped version (so it does not nag).
    """
    copied, modified = await hass.async_add_executor_job(
        _deploy, hass.config.config_dir, force
    )
    if copied < 0:
        return -1
    if copied > 0:
        _LOGGER.info("Deployed %d Switch Manager blueprint file(s)", copied)
    if force:
        persistent_notification.async_dismiss(hass, NOTIFICATION_ID)
    elif modified:
        to_notify = await hass.async_add_executor_job(
            _gate_notification, hass.config.config_dir, modified
        )
        if to_notify:
            persistent_notification.async_create(
                hass,
                (
                    "A newer Switch Manager blueprint is available but the "
                    "deployed copy was changed (by you or Switch Manager) and "
                    f"was kept: {', '.join(to_notify)}.\n\n"
                    "Press **Deploy Switch Manager Blueprints (Force)** on the "
                    "gateway device to overwrite it with the bundled version."
                ),
                title="Lunatone DALI-2: blueprint update available",
                notification_id=NOTIFICATION_ID,
            )
    return copied
