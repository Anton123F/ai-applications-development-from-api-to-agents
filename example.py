import asyncio
import time


def brew_coffee_sync():
    """Sync — blocks the ENTIRE program. Nothing else can run."""
    print("  [sync]  coffee started")
    time.sleep(2)                     # freezes everything, no other code runs
    print("  [sync]  coffee ready")
    return "☕ coffee"


async def brew_coffee_async():
    """Async — pauses only THIS coroutine. Others can run during the wait."""
    print("  [async] coffee started")
    await asyncio.sleep(2)            # yields control to event loop
    print("  [async] coffee ready")
    return "☕ coffee"


async def brew_tea_async():
    print("  [async] tea started")
    await asyncio.sleep(1)
    print("  [async] tea ready")
    return "🍵 tea"


async def main():
    # --- sync version: tea has to WAIT for coffee to even start ---
    print("=== SYNC: coffee + tea (total ~3s) ===")
    start = time.time()
    coffee = brew_coffee_sync()       # blocks 2s — tea cannot start yet
    tea = brew_coffee_sync()          # blocks 2s — only starts after coffee
    print(f"Done in {time.time() - start:.1f}s\n")

    # --- async version: tea starts immediately, runs while coffee brews ---
    print("=== ASYNC: coffee + tea (total ~2s) ===")
    start = time.time()
    coffee, tea = await asyncio.gather(brew_coffee_async(), brew_tea_async())
    print(f"Done in {time.time() - start:.1f}s\n")

    # --- THIS is why you can't just use a sync function with gather ---
    print("=== BROKEN: sync function inside gather ===")
    print("  gather won't help — time.sleep() blocks the event loop itself")
    print("  tea cannot start until coffee's time.sleep() finishes")
    print("  sync functions have no yield point for the event loop to switch on")


asyncio.run(main())
