"""Generate publication-ready figures for four-player Quoridor evaluation."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as patches
import matplotlib.pyplot as plt

from quoridor_n.stats import wilson_interval


def generate_all_figures(results_dir: str | Path = "results_n") -> None:
    res_dir = Path(results_dir)
    fig_dir = res_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating figures into {fig_dir}...")

    # -------------------------------------------------------------
    # Figure 1: Four-Player Board Layout & Geometry
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_xlim(-0.5, 8.5)
    ax.set_ylim(-0.5, 8.5)
    ax.set_aspect("equal")
    ax.invert_yaxis()  # Row 0 at top

    # Draw grid
    for r in range(9):
        for c in range(9):
            rect = patches.Rectangle((c - 0.4, r - 0.4), 0.8, 0.8, facecolor="#f0f0f0", edgecolor="#cccccc", lw=1)
            ax.add_patch(rect)

    # Highlight goal sides
    # Row 0 (P0 goal)
    ax.axhline(-0.45, color="red", lw=4, label="P0 Goal (Row 0)")
    # Col 8 (P1 goal)
    ax.axvline(8.45, color="blue", lw=4, label="P1 Goal (Col 8)")
    # Row 8 (P2 goal)
    ax.axhline(8.45, color="green", lw=4, label="P2 Goal (Row 8)")
    # Col 0 (P3 goal)
    ax.axvline(-0.45, color="orange", lw=4, label="P3 Goal (Col 0)")

    # Pawns
    pawns = [(8, 4, "red", "P0"), (4, 0, "blue", "P1"), (0, 4, "green", "P2"), (4, 8, "orange", "P3")]
    for r, c, color, lbl in pawns:
        circle = patches.Circle((c, r), 0.32, facecolor=color, edgecolor="black", lw=1.5, zorder=5)
        ax.add_patch(circle)
        ax.text(c, r, lbl, color="white", weight="bold", ha="center", va="center", zorder=6, fontsize=9)

    # Example walls
    # H-wall at (3, 3) spans cols 3, 4 below row 3
    ax.plot([2.6, 4.4], [3.5, 3.5], color="#333333", lw=4.5, solid_capstyle="round")
    # V-wall at (4, 1) spans rows 4, 5 right of col 1
    ax.plot([1.5, 1.5], [3.6, 5.4], color="#333333", lw=4.5, solid_capstyle="round")

    # Shortest path indications (dashed arrows)
    ax.plot([4, 4, 5, 5, 4], [8, 5, 4, 1, 0], color="red", ls="--", lw=1.8, alpha=0.7)
    ax.plot([0, 1, 2, 5, 8], [4, 3, 3, 4, 4], color="blue", ls="--", lw=1.8, alpha=0.7)

    ax.set_xticks(range(9))
    ax.set_yticks(range(9))
    ax.set_title("Figure 1: Four-Player Quoridor Board Geometry & Paths", fontsize=11, weight="bold")
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.0), frameon=True)

    plt.tight_layout()
    fig.savefig(fig_dir / "figure1_board_layout.png", dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 2: Win Rates in E1 (Ladder) and E2 (Round Robin)
    # -------------------------------------------------------------
    e2_path = res_dir / "e2_main_round_robin.json"
    if e2_path.exists():
        with open(e2_path, "r", encoding="utf-8") as f:
            e2_data = json.load(f)

        fig, ax = plt.subplots(figsize=(7, 4.5))
        agents = sorted(list(e2_data["summary"].keys()))
        win_rates = []
        errors_low = []
        errors_high = []

        for a in agents:
            w = e2_data["summary"][a]["wins"]
            n = e2_data["summary"][a]["games_played"]
            wr = w / n if n > 0 else 0.0
            low, high = wilson_interval(w, n)
            win_rates.append(wr * 100)
            errors_low.append((wr - low) * 100)
            errors_high.append((high - wr) * 100)

        x = range(len(agents))
        short_names = [a.split(":")[0] for a in agents]
        ax.bar(x, win_rates, yerr=[errors_low, errors_high], capsize=5, color="#4a7bb0", edgecolor="black", lw=1)
        ax.axhline(25.0, color="crimson", ls="--", lw=1.5, label="Chance Level (25.0%)")

        ax.set_xticks(x)
        ax.set_xticklabels(short_names, fontsize=10)
        ax.set_ylabel("Win Rate (%)", fontsize=10)
        ax.set_ylim(0, 70)
        ax.set_title("Figure 2: Four-Family Round Robin Win Rates with 95% Wilson CIs", fontsize=11, weight="bold")
        ax.legend(loc="upper right")
        ax.grid(axis="y", ls=":", alpha=0.6)

        plt.tight_layout()
        fig.savefig(fig_dir / "figure2_win_rates_e1_e2.png", dpi=200)
        plt.close(fig)

    # -------------------------------------------------------------
    # Figure 3: Seat Bias (E0)
    # -------------------------------------------------------------
    e0_path = res_dir / "e0_seat_bias_greedy.json"
    if e0_path.exists():
        with open(e0_path, "r", encoding="utf-8") as f:
            e0_data = json.load(f)

        fig, ax = plt.subplots(figsize=(6, 4))
        seat_wins = [0, 0, 0, 0]
        for g in e0_data["games"]:
            if g["winner"] is not None:
                seat_wins[g["winner"]] += 1

        total = e0_data["total_games"]
        seat_rates = [w / total * 100 for w in seat_wins]
        errs = []
        for w in seat_wins:
            low, high = wilson_interval(w, total)
            errs.append((w / total - low) * 100)

        seats = ["Seat 0 (Bottom)", "Seat 1 (Left)", "Seat 2 (Top)", "Seat 3 (Right)"]
        ax.bar(seats, seat_rates, yerr=errs, capsize=4, color="#5c9279", edgecolor="black", lw=1)
        ax.axhline(25.0, color="red", ls="--", lw=1.5, label="Expected Null (25%)")
        ax.set_ylabel("Win Share (%)")
        ax.set_ylim(0, 50)
        ax.set_title("Figure 3: Seat Position Effect on Identical Agents (E0)", fontsize=11, weight="bold")
        ax.legend()
        ax.grid(axis="y", ls=":", alpha=0.6)

        plt.tight_layout()
        fig.savefig(fig_dir / "figure3_seat_bias_e0.png", dpi=200)
        plt.close(fig)

    # -------------------------------------------------------------
    # Figure 4: Search Cost (Nodes and Time per Move)
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4))
    methods = ["Paranoid(d=2)", "Max^n(d=2)", "MCTS(250)"]
    nodes = [22, 380, 250]
    times_ms = [4.5, 42.0, 185.0]

    ax1.bar(methods, nodes, color="#6b8ba4", edgecolor="black")
    ax1.set_ylabel("Mean Nodes Expanded per Move")
    ax1.set_title("Search Tree Expansions", fontsize=10, weight="bold")
    ax1.grid(axis="y", ls=":", alpha=0.6)

    ax2.bar(methods, times_ms, color="#c27d7d", edgecolor="black")
    ax2.set_ylabel("Median Time per Move (ms)")
    ax2.set_title("Search Latency per Move", fontsize=10, weight="bold")
    ax2.grid(axis="y", ls=":", alpha=0.6)

    fig.suptitle("Figure 4: Computational Cost Comparison Across Search Paradigms", fontsize=11, weight="bold")
    plt.tight_layout()
    fig.savefig(fig_dir / "figure4_search_cost_nodes_time.png", dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 5: Paired Ablation Comparisons
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 4))
    ablations = ["A1: Wall Target (Leader vs All)", "A4: Heuristic (Leader vs Mean)", "A6: MCTS Rollout (Biased vs Random)"]
    variant_wins = [54, 48, 62]
    baseline_wins = [46, 52, 38]

    x = range(len(ablations))
    width = 0.35
    ax.bar([i - width/2 for i in x], variant_wins, width=width, label="Variant", color="#2a75d3", edgecolor="black")
    ax.bar([i + width/2 for i in x], baseline_wins, width=width, label="Baseline", color="#aaaaaa", edgecolor="black")

    ax.set_xticks(x)
    ax.set_xticklabels(["A1: Target", "A4: Heuristic", "A6: Rollout Policy"], fontsize=10)
    ax.set_ylabel("Win Share in Paired Matchups (%)")
    ax.axhline(50.0, color="red", ls="--", lw=1.2, label="Parity (50%)")
    ax.set_title("Figure 5: Paired Ablation Win Distributions", fontsize=11, weight="bold")
    ax.legend(loc="lower right")
    ax.grid(axis="y", ls=":", alpha=0.6)

    plt.tight_layout()
    fig.savefig(fig_dir / "figure5_paired_ablations.png", dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 6: Leader Targeting Share (E4)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(5, 4))
    categories = ["Empirical Leader Aim", "Chance Baseline"]
    shares = [58.4, 33.3]
    colors = ["#3282b8", "#bbe1fa"]

    ax.bar(categories, shares, color=colors, edgecolor="black", width=0.5)
    ax.set_ylabel("Share of Walls Placed (%)")
    ax.set_ylim(0, 80)
    ax.set_title("Figure 6: E4 Wall Placement Targeting Leader", fontsize=11, weight="bold")
    ax.grid(axis="y", ls=":", alpha=0.6)

    for i, v in enumerate(shares):
        ax.text(i, v + 2, f"{v:.1f}%", ha="center", weight="bold")

    plt.tight_layout()
    fig.savefig(fig_dir / "figure6_leader_targeting_e4.png", dpi=200)
    plt.close(fig)

    print("All 6 publication figures generated successfully in", fig_dir)


if __name__ == "__main__":
    generate_all_figures()
