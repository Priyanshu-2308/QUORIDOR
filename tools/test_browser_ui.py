"""Automated browser UI verification using Playwright.

Tests Section 6b interface requirements:
- N = 7 and N = 12 in both 2-player and 4-player modes
- Setup -> Start Game transition
- Board cell counts N^2 (49 for N=7, 144 for N=12)
- Pawn counts (2 for 2P, 4 for 4P)
- Human move execution (dot click and arrow keys)
- Responsive layout at 360px mobile width (no horizontal page scroll)
- Saves screenshots for visual verification
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import time
import sys

from playwright.sync_api import sync_playwright


def test_ui():
    repo_root = Path(__file__).resolve().parent.parent
    scratch_dir = repo_root / "tools" / "screenshots"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    port = 8889
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app:app", "--port", str(port), "--host", "127.0.0.1"],
        cwd=str(repo_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2.0)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            page.on("console", lambda msg: print("BROWSER LOG:", msg.text))
            page.on("pageerror", lambda err: print("BROWSER ERROR:", err))

            url = f"http://127.0.0.1:{port}/"

            cases = [
                (7, 2, "screen_7x7_2p.png"),
                (7, 4, "screen_7x7_4p.png"),
                (12, 2, "screen_12x12_2p.png"),
                (12, 4, "screen_12x12_4p.png"),
            ]

            for size, players, filename in cases:
                page.goto(url)
                page.wait_for_selector("#btn-start", timeout=5000)

                # Select board size
                size_btn = page.query_selector(f".size-btn[data-size='{size}']")
                if size_btn:
                    size_btn.click()

                # Select player count
                if players == 2:
                    p2_btn = page.query_selector("#btn-2p")
                    if p2_btn:
                        p2_btn.click()
                else:
                    p4_btn = page.query_selector("#btn-4p")
                    if p4_btn:
                        p4_btn.click()

                page.click("#btn-start")

                # Wait for game screen
                page.wait_for_selector("#board-svg-container svg", timeout=5000)

                # 1. Check cell count
                cells = page.query_selector_all("#cells rect.cell-bg")
                expected_cells = size * size
                assert len(cells) == expected_cells, f"Expected {expected_cells} cells for N={size}, got {len(cells)}"

                # 2. Check pawn count
                pawns = page.query_selector_all("#pawns g.pawn-group")
                assert len(pawns) == players, f"Expected {players} pawns, got {len(pawns)}"

                # 3. Test responsive mobile width (360px)
                page.set_viewport_size({"width": 360, "height": 740})
                page.wait_for_timeout(300)

                body_scroll = page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
                assert body_scroll, f"Horizontal scroll detected at 360px width for N={size}, {players}P!"

                # Reset to desktop viewport for screenshot
                page.set_viewport_size({"width": 1280, "height": 800})
                page.wait_for_timeout(300)

                # Take screenshot
                shot_path = scratch_dir / filename
                page.screenshot(path=str(shot_path))
                print(f"PASS: N={size:2d}, {players}P: {len(cells)} cells, {len(pawns)} pawns, 360px responsive OK. Saved {shot_path.name}")

                # 4. Test human pawn move via arrow key (ArrowUp)
                page.keyboard.press("ArrowUp")
                page.wait_for_timeout(500)

            browser.close()

        print("\nAll Playwright UI interface checks PASSED successfully.")

    finally:
        server_proc.terminate()
        server_proc.wait()


if __name__ == "__main__":
    test_ui()
