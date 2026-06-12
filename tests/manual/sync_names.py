"""Sync device names from a CSV file to the gateway.

CSV format (semicolon separated, header required): line;address;name
Devices are matched by (line, address); names are written via
PUT /device/{id} — only the name field, group assignments stay untouched.

Usage:
  python tests/manual/sync_names.py <host> <names.csv>          # dry run
  python tests/manual/sync_names.py <host> <names.csv> --apply  # write
"""

import asyncio
import csv
import sys

import aiohttp


def load_names(path: str) -> dict[tuple[int, int], str]:
    names: dict[tuple[int, int], str] = {}
    with open(path, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            name = row["name"].strip()
            if name:
                names[(int(row["line"]), int(row["address"]))] = name
    return names


async def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("usage: sync_names.py <host> <names.csv> [--apply]")
    host, csv_path = sys.argv[1], sys.argv[2]
    apply = "--apply" in sys.argv[3:]
    names = load_names(csv_path)

    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://{host}/devices", timeout=15) as response:
            devices = (await response.json())["devices"]

        changes = []
        for device in devices:
            wanted = names.get((device["line"], device["address"]))
            if wanted and wanted != device["name"]:
                changes.append((device, wanted))

        if not changes:
            print("nothing to do, all names match")
            return

        for device, wanted in changes:
            print(
                f"line {device['line']} addr {device['address']:>2} (id {device['id']:>3}): "
                f"'{device['name']}' -> '{wanted}'"
            )
        if not apply:
            print(f"\nDRY RUN: {len(changes)} name(s) would change. Re-run with --apply.")
            return

        for device, wanted in changes:
            async with session.put(
                f"http://{host}/device/{device['id']}",
                json={"name": wanted},
                timeout=10,
            ) as response:
                status = "OK" if response.status < 400 else f"HTTP {response.status}"
                print(f"id {device['id']:>3} -> '{wanted}': {status}")

        print(f"\ndone, {len(changes)} name(s) updated")


if __name__ == "__main__":
    asyncio.run(main())
