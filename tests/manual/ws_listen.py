"""Passively listen to the Lunatone gateway websocket and log every message.

Read-only reconnaissance: connects, never sends anything, records all frames.
Usage: python tests/manual/ws_listen.py <host> [seconds] [outfile]
The host can also be provided via the LUNATONE_GW_HOST environment variable.
"""

import asyncio
import json
import os
import sys
import time

import aiohttp

HOST = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LUNATONE_GW_HOST")
if not HOST:
    sys.exit("usage: ws_listen.py <host> [seconds] [outfile] (or set LUNATONE_GW_HOST)")
DURATION = int(sys.argv[2]) if len(sys.argv) > 2 else 90
OUTFILE = sys.argv[3] if len(sys.argv) > 3 else "ws_capture.jsonl"


async def main() -> None:
    url = f"ws://{HOST}:80"
    deadline = time.monotonic() + DURATION
    count = 0
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url, timeout=10) as ws:
            print(f"connected to {url}, listening {DURATION}s ...", flush=True)
            with open(OUTFILE, "w", encoding="utf-8") as f:
                while time.monotonic() < deadline:
                    try:
                        msg = await ws.receive(timeout=deadline - time.monotonic())
                    except asyncio.TimeoutError:
                        break
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        count += 1
                        try:
                            data = json.loads(msg.data)
                            mtype = data.get("type")
                        except ValueError:
                            data, mtype = msg.data, "<raw>"
                        f.write(json.dumps({"t": time.time(), "msg": data}) + "\n")
                        f.flush()
                        preview = json.dumps(data)[:300]
                        print(f"[{count}] type={mtype}: {preview}", flush=True)
                    elif msg.type in (
                        aiohttp.WSMsgType.CLOSED,
                        aiohttp.WSMsgType.ERROR,
                    ):
                        print(f"socket closed: {msg.type}", flush=True)
                        break
    print(f"done, {count} messages captured -> {OUTFILE}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
