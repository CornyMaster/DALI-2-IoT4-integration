"""Read-only dry run against a real gateway.

Shows exactly which entities the integration would create, without Home
Assistant and without sending a single write to the gateway (the REST client
is constructed with read_only=True).

Usage: python tests/manual/dry_run.py <host>  (or set LUNATONE_GW_HOST)
"""

import asyncio
import os
import sys
import types
from pathlib import Path

import aiohttp

# Import submodules without executing the package __init__ (which needs HA)
REPO_ROOT = Path(__file__).resolve().parents[2]
for pkg_name, pkg_path in (
    ("custom_components", REPO_ROOT / "custom_components"),
    ("custom_components.dali_lunatone", REPO_ROOT / "custom_components" / "dali_lunatone"),
):
    module = types.ModuleType(pkg_name)
    module.__path__ = [str(pkg_path)]
    sys.modules.setdefault(pkg_name, module)

from custom_components.dali_lunatone.api import LunatoneRestClient  # noqa: E402
from custom_components.dali_lunatone.models import LunatoneData  # noqa: E402
from custom_components.dali_lunatone.websocket import LunatoneWsListener  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LUNATONE_GW_HOST")
if not HOST:
    sys.exit("usage: dry_run.py <host> (or set LUNATONE_GW_HOST)")

ENTRY_ID = "ENTRYID"


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        client = LunatoneRestClient(session, HOST, read_only=True)
        info = await client.async_get_info()
        devices = await client.async_get_devices()
        sensors = await client.async_get_sensors()
        data = LunatoneData.from_api(info, devices)

        print(f"Gateway: {data.info.name} {data.info.version}")
        print(f"Lines reported: {data.info.lines}, line status: {data.info.line_status}")
        print(f"Devices: {len(data.devices)} on lines {data.lines_with_devices()}")
        print(f"Configured /sensors entries: {len(sensors)}")
        print()

        print("== Device lights ==")
        for device in sorted(data.devices.values(), key=lambda d: (d.line, d.address)):
            print(
                f"  light {ENTRY_ID}_line{device.line}_dali_{device.address:<3}"
                f" gw_id={device.gw_id:<3} '{device.name}' groups={device.groups}"
                f" on={device.is_on} dim={device.brightness_pct}"
            )

        print("\n== Group lights (per line!) ==")
        for (line, group), members in sorted(data.groups_with_members().items()):
            print(
                f"  light {ENTRY_ID}_line{line}_group{group}  "
                f"'Line {line} Group {group}'  members={len(members)}"
            )

        print("\n== Broadcast lights ==")
        for line in data.lines_with_devices():
            print(f"  light {ENTRY_ID}_line{line}_broadcast  'Line {line} Broadcast'")

        # sanity: unique ids must be collision-free
        unique_ids = [
            f"{ENTRY_ID}_line{d.line}_dali_{d.address}" for d in data.devices.values()
        ]
        assert len(set(unique_ids)) == len(unique_ids), "unique_id collision!"
        print(f"\nOK: {len(unique_ids)} device unique_ids, no collisions")

        print("\n== Passive websocket listen (15s, press a wall switch to test) ==")
        received: list = []

        listener = LunatoneWsListener(
            session,
            HOST,
            on_input_event=lambda event: (received.append(event), print(f"  input event: {event}")),
            on_devices_update=lambda devs: print(f"  devices push: {len(devs)} device(s) updated"),
        )
        await listener.async_start()
        await asyncio.sleep(15)
        connected = listener.connected
        await listener.async_stop()
        print(f"websocket connected: {connected}, input events seen: {len(received)}")


if __name__ == "__main__":
    asyncio.run(main())
