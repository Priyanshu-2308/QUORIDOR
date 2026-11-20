"""Statistical analysis and figure generation for dynamic-board Quoridor results."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from quoridor_n.stats import (
    clustered_bootstrap_mean_ci,
    exact_two_sided_binomial_p,
    holm_bonferroni,
    mean_rank_bootstrap_ci,
    paired_sign_test,
    power_binomial,
    sample_size_binomial,
    wilson_interval,
)


def load_json(p: Path) -> dict[str, Any]:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_all(results_dir: str = "results_n") -> None:
    res_p = Path(results_dir)
    raw_p = res_p / "raw"
    fig_p = res_p / "figures"
    fig_p.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, Any]] = []
    ablation_rows: list[dict[str, Any]] = []
    stats_lines: list[str] = []

    stats_lines.append("================================================================================")
    stats_lines.append("DYNAMIC-BOARD QUORIDOR: STATISTICAL REPORT AND HYPOTHESIS EVALUATION")
    stats_lines.append("================================================================================\n")

    # -------------------------------------------------------------------------
    # 1. E0: Seat Bias
    # -------------------------------------------------------------------------
    stats_lines.append("--------------------------------------------------------------------------------")
    stats_lines.append("1. EXPERIMENT E0: SEAT BIAS ANALYSIS (9x9)")
    stats_lines.append("--------------------------------------------------------------------------------")

    for f_name, mode, expected_p0 in [
        ("e0_seat_bias_4p_greedy.json", "4P Greedy", 0.25),
        ("e0_seat_bias_4p_paranoid.json", "4P Paranoid", 0.25),
        ("e0_seat_bias_2p_greedy.json", "2P Greedy", 0.50),
        ("e0_seat_bias_2p_paranoid.json", "2P Paranoid", 0.50),
    ]:
        fp = raw_p / f_name
        if not fp.exists():
            continue
        data = load_json(fp)
        games = data.get("games", [])
        total_g = len(games)
        stats_lines.append(f"\n{mode} ({total_g} games planned vs played: {total_g}):")

        seat_wins: dict[int, int] = {p: 0 for p in (range(4) if "4p" in f_name else [0, 2])}
        for g in games:
            w = g["winner"]
            if w in seat_wins:
                seat_wins[w] += 1

        for seat, wins in seat_wins.items():
            rate = wins / total_g if total_g > 0 else 0.0
            low, high = wilson_interval(wins, total_g)
            p_val = exact_two_sided_binomial_p(wins, total_g, expected_p0)
            stats_lines.append(
                f"  Seat {seat}: win rate = {rate*100:.1f}% ({wins}/{total_g}), 95% CI [{low*100:.1f}%, {high*100:.1f}%], p = {p_val:.4f}"
            )
            summary_rows.append({
                "experiment": f"E0_{f_name.replace('.json', '')}",
                "table": mode,
                "size": data.get("board_size", 9),
                "players": data.get("num_players", 4 if "4p" in f_name else 2),
                "games_played": total_g,
                "agent": f"Seat_{seat}",
                "wins": wins,
                "win_rate": f"{rate:.4f}",
                "ci_low": f"{low:.4f}",
                "ci_high": f"{high:.4f}",
                "p_value": f"{p_val:.4f}",
                "mean_rank": "",
                "mean_plies": f"{sum(g['plies'] for g in games)/max(1, total_g):.1f}",
                "mean_nodes": "",
                "mean_time_s": "",
            })

    # -------------------------------------------------------------------------
    # 2. E1: Skill Ladder
    # -------------------------------------------------------------------------
    stats_lines.append("\n--------------------------------------------------------------------------------")
    stats_lines.append("2. EXPERIMENT E1: SKILL LADDER (vs Greedy Baselines)")
    stats_lines.append("--------------------------------------------------------------------------------")

    ladder_files = [
        ("e1_ladder_4p_paranoid.json", "paranoid", 4, 0.25),
        ("e1_ladder_4p_maxn.json", "maxn", 4, 0.25),
        ("e1_ladder_4p_mcts.json", "mcts", 4, 0.25),
        ("e1_ladder_2p_paranoid.json", "paranoid", 2, 0.50),
        ("e1_ladder_2p_mcts.json", "mcts", 2, 0.50),
    ]

    h1_p_vals = []
    h1_records = []

    for f_name, ag_name, num_p, p0 in ladder_files:
        fp = raw_p / f_name
        if not fp.exists():
            continue
        data = load_json(fp)
        summary = data.get("summary", {})
        target_spec = next((sp for sp in summary.keys() if ag_name in sp), None)
        if not target_spec:
            continue

        ag_data = summary[target_spec]
        wins = ag_data["wins"]
        total_g = ag_data["games_played"]
        rate = ag_data["win_rate"]
        low, high = wilson_interval(wins, total_g)
        p_val = exact_two_sided_binomial_p(wins, total_g, p0)
        h1_p_vals.append(p_val)
        h1_records.append((f"{num_p}P {ag_name}", wins, total_g, rate, low, high, p_val))

        mean_r = ag_data["mean_rank"]
        summary_rows.append({
            "experiment": f"E1_{num_p}P",
            "table": f"{num_p}P_ladder",
            "size": data.get("board_size", 9),
            "players": num_p,
            "games_played": total_g,
            "agent": target_spec,
            "wins": wins,
            "win_rate": f"{rate:.4f}",
            "ci_low": f"{low:.4f}",
            "ci_high": f"{high:.4f}",
            "p_value": f"{p_val:.4f}",
            "mean_rank": f"{mean_r:.2f}",
            "mean_plies": f"{sum(g['plies'] for g in data.get('games', []))/max(1, total_g):.1f}",
            "mean_nodes": f"{ag_data.get('mean_nodes_per_move', 0.0):.1f}",
            "mean_time_s": f"{ag_data.get('mean_time_per_move', 0.0):.4f}",
        })

    # Apply Holm correction for H1
    if h1_p_vals:
        holm_h1 = holm_bonferroni(h1_p_vals)
        for (label, wins, total_g, rate, low, high, raw_pval), (_, adj_p, is_sig) in zip(h1_records, holm_h1):
            stats_lines.append(
                f"  {label}: win rate = {rate*100:.1f}% ({wins}/{total_g}), 95% CI [{low*100:.1f}%, {high*100:.1f}%], raw p = {raw_pval:.4e}, adj p = {adj_p:.4e} {'*' if is_sig else ''}"
            )

    # -------------------------------------------------------------------------
    # 3. E2: Main Round Robin (4P, 9x9, 168 games)
    # -------------------------------------------------------------------------
    stats_lines.append("\n--------------------------------------------------------------------------------")
    stats_lines.append("3. EXPERIMENT E2: MAIN ROUND ROBIN (4P 9x9 Omniverse Table)")
    stats_lines.append("--------------------------------------------------------------------------------")

    e2_file = raw_p / "e2_main_round_robin.json"
    if e2_file.exists():
        e2_data = load_json(e2_file)
        e2_games = e2_data.get("games", [])
        total_e2 = len(e2_games)
        stats_lines.append(f"Planned games: {e2_data.get('games_planned')}, Played: {total_e2}")

        e2_summary = e2_data.get("summary", {})
        for sp, sdata in e2_summary.items():
            w = sdata["wins"]
            n = sdata["games_played"]
            wr = sdata["win_rate"]
            low, high = wilson_interval(w, n)
            p_val = exact_two_sided_binomial_p(w, n, 0.25)
            mr = sdata["mean_rank"]
            mr_val, mr_low, mr_high = mean_rank_bootstrap_ci(sdata["ranks"])

            stats_lines.append(
                f"  {sp:25s}: wins={w:2d}/{n} ({wr*100:.1f}%, 95% CI [{low*100:.1f}%, {high*100:.1f}%], p={p_val:.4f}) | mean rank={mr_val:.2f} [{mr_low:.2f}, {mr_high:.2f}] | time/move={sdata.get('mean_time_per_move', 0.0):.4f}s"
            )
            summary_rows.append({
                "experiment": "E2_RoundRobin",
                "table": "Omniverse_4P",
                "size": 9,
                "players": 4,
                "games_played": n,
                "agent": sp,
                "wins": w,
                "win_rate": f"{wr:.4f}",
                "ci_low": f"{low:.4f}",
                "ci_high": f"{high:.4f}",
                "p_value": f"{p_val:.4f}",
                "mean_rank": f"{mr_val:.2f}",
                "mean_plies": f"{sum(g['plies'] for g in e2_games)/max(1, total_e2):.1f}",
                "mean_nodes": f"{sdata.get('mean_nodes_per_move', 0.0):.1f}",
                "mean_time_s": f"{sdata.get('mean_time_per_move', 0.0):.4f}",
            })

        # Pairwise Sign Tests with Holm Correction
        stats_lines.append("\n  Pairwise Paired Sign Tests across 6 Pairings:")
        agents = list(e2_summary.keys())
        pairwise_records = []
        raw_ps = []

        for i in range(len(agents)):
            for j in range(i + 1, len(agents)):
                ag_a, ag_b = agents[i], agents[j]
                a_beats_b = 0
                b_beats_a = 0
                for g in e2_games:
                    # Ranks in this game
                    rank_a = None
                    rank_b = None
                    for pid_str, st in g["seat_stats"].items():
                        if st["spec"] == ag_a:
                            rank_a = g["ranks"][pid_str]
                        elif st["spec"] == ag_b:
                            rank_b = g["ranks"][pid_str]
                    if rank_a is not None and rank_b is not None:
                        if rank_a < rank_b:
                            a_beats_b += 1
                        elif rank_b < rank_a:
                            b_beats_a += 1

                p_pair = paired_sign_test(a_beats_b, b_beats_a)
                raw_ps.append(p_pair)
                pairwise_records.append((ag_a, ag_b, a_beats_b, b_beats_a, p_pair))

        holm_pairs = holm_bonferroni(raw_ps)
        for (ag_a, ag_b, wa, wb, rp), (_, adj_p, is_sig) in zip(pairwise_records, holm_pairs):
            short_a = ag_a.split(":")[0]
            short_b = ag_b.split(":")[0]
            stats_lines.append(
                f"    {short_a} vs {short_b:8s}: {wa} vs {wb} (decisive n={wa+wb}) | raw p={rp:.4e}, adj p={adj_p:.4e} {'*' if is_sig else ''}"
            )

    # -------------------------------------------------------------------------
    # 4. E3 & E3b: Family Comparison & 2P Match
    # -------------------------------------------------------------------------
    stats_lines.append("\n--------------------------------------------------------------------------------")
    stats_lines.append("4. EXPERIMENT E3 & E3b: FAMILY & 2-PLAYER HEAD-TO-HEAD")
    stats_lines.append("--------------------------------------------------------------------------------")

    e3_file = raw_p / "e3_family_comparison.json"
    if e3_file.exists():
        e3_data = load_json(e3_file)
        e3_games = e3_data.get("games", [])
        stats_lines.append(f"\nE3: 2 Paranoid vs 2 MCTS (Played {len(e3_games)} games):")
        paranoid_wins = 0
        mcts_wins = 0
        for g in e3_games:
            w = g["winner"]
            if w is not None:
                spec = g["seat_stats"][str(w)]["spec"]
                if "paranoid" in spec:
                    paranoid_wins += 1
                elif "mcts" in spec:
                    mcts_wins += 1
        total_decisive = paranoid_wins + mcts_wins
        p_val_e3 = exact_two_sided_binomial_p(paranoid_wins, total_decisive, 0.50)
        low, high = wilson_interval(paranoid_wins, total_decisive)
        stats_lines.append(
            f"  Paranoid Family: {paranoid_wins}/{total_decisive} ({paranoid_wins/max(1, total_decisive)*100:.1f}%, 95% CI [{low*100:.1f}%, {high*100:.1f}%], p={p_val_e3:.4f})"
        )

    e3b_file = raw_p / "e3b_two_player_match.json"
    if e3b_file.exists():
        e3b_data = load_json(e3b_file)
        e3b_games = e3b_data.get("games", [])
        stats_lines.append(f"\nE3b: 2P Alpha-Beta vs MCTS (Played {len(e3b_games)} games):")
        p_wins = 0
        m_wins = 0
        for g in e3b_games:
            w = g["winner"]
            if w is not None:
                spec = g["seat_stats"][str(w)]["spec"]
                if "paranoid" in spec:
                    p_wins += 1
                elif "mcts" in spec:
                    m_wins += 1
        tot_b = p_wins + m_wins
        p_val_b = exact_two_sided_binomial_p(p_wins, tot_b, 0.50)
        low, high = wilson_interval(p_wins, tot_b)
        stats_lines.append(
            f"  Alpha-Beta win rate: {p_wins}/{tot_b} ({p_wins/max(1, tot_b)*100:.1f}%, 95% CI [{low*100:.1f}%, {high*100:.1f}%], p={p_val_b:.4f})"
        )

    # -------------------------------------------------------------------------
    # 5. E4: Leader Targeting vs Placebo Baseline
    # -------------------------------------------------------------------------
    stats_lines.append("\n--------------------------------------------------------------------------------")
    stats_lines.append("5. EXPERIMENT E4: LEADER TARGETING BEHAVIORAL ANALYSIS")
    stats_lines.append("--------------------------------------------------------------------------------")

    e4_file = raw_p / "e4_targeting.json"
    if e4_file.exists():
        e4_data = load_json(e4_file)
        tot_w = e4_data["total_walls"]
        tot_ld = e4_data["total_leader_delayed"]
        tot_lo = e4_data["total_leader_only"]
        tot_ph = e4_data["total_placebo_hits"]
        tot_pc = e4_data["total_placebo_candidates"]

        hit_rate = tot_ld / max(1, tot_w)
        only_rate = tot_lo / max(1, tot_w)
        placebo_rate = tot_ph / max(1, tot_pc)

        # Clustered bootstrap over games
        game_clusters = []
        for gr in e4_data["game_records"]:
            gw = gr["total_walls"]
            if gw > 0:
                # Array of 1s and 0s for walls in this game
                g_hits = [1.0] * gr["leader_delayed"] + [0.0] * (gw - gr["leader_delayed"])
                game_clusters.append(g_hits)

        b_mean, b_low, b_high = clustered_bootstrap_mean_ci(game_clusters)

        stats_lines.append(f"Total Walls Placed Analyzed: {tot_w} across {e4_data['games_analyzed']} games")
        stats_lines.append(f"  Share lengthening leader path: {hit_rate*100:.1f}% (Clustered 95% CI: [{b_low*100:.1f}%, {b_high*100:.1f}%])")
        stats_lines.append(f"  Share where leader was ONLY opponent affected: {only_rate*100:.1f}%")
        stats_lines.append(f"  Placebo baseline (random legal candidate wall hit leader): {placebo_rate*100:.1f}% ({tot_ph}/{tot_pc})")
        stats_lines.append(f"  Advantage over placebo: +{(hit_rate - placebo_rate)*100:.1f} percentage points")

    # -------------------------------------------------------------------------
    # 6. E5: Board Size Study
    # -------------------------------------------------------------------------
    stats_lines.append("\n--------------------------------------------------------------------------------")
    stats_lines.append("6. EXPERIMENT E5: BOARD SIZE SCALING (N in 7..12)")
    stats_lines.append("--------------------------------------------------------------------------------")

    sizes = list(range(7, 13))
    size_2p_records = []
    size_4p_records = []

    for n in sizes:
        f2 = raw_p / f"e5_size_{n}_2p.json"
        f4 = raw_p / f"e5_size_{n}_4p.json"

        if f2.exists():
            d2 = load_json(f2)
            g2 = d2.get("games", [])
            p_wins = sum(1 for g in g2 if g["winner"] == 0)
            tot_g = len(g2)
            mean_pl = sum(g["plies"] for g in g2) / max(1, tot_g)
            size_2p_records.append((n, tot_g, p_wins, mean_pl))

        if f4.exists():
            d4 = load_json(f4)
            g4 = d4.get("games", [])
            tot_g = len(g4)
            mean_pl = sum(g["plies"] for g in g4) / max(1, tot_g)
            # Seat 0 wins
            s0_wins = sum(1 for g in g4 if g["winner"] == 0)
            size_4p_records.append((n, tot_g, s0_wins, mean_pl))

    stats_lines.append("Board Size Scaling 2-Player (Paranoid vs MCTS):")
    for n, tot_g, pw, pl in size_2p_records:
        rate = pw / max(1, tot_g)
        low, high = wilson_interval(pw, tot_g)
        stats_lines.append(f"  N={n:2d}: Paranoid win rate = {rate*100:.1f}% ({pw}/{tot_g}, 95% CI [{low*100:.1f}%, {high*100:.1f}%]) | mean plies = {pl:.1f}")

    stats_lines.append("\nBoard Size Scaling 4-Player (Seat 0 Advantage):")
    for n, tot_g, s0, pl in size_4p_records:
        rate = s0 / max(1, tot_g)
        low, high = wilson_interval(s0, tot_g)
        stats_lines.append(f"  N={n:2d}: Seat 0 win rate = {rate*100:.1f}% ({s0}/{tot_g}, 95% CI [{low*100:.1f}%, {high*100:.1f}%]) | mean plies = {pl:.1f}")

    # Contrast 7x7 vs 12x12
    if len(size_4p_records) >= 6:
        n7_rec = size_4p_records[0]
        n12_rec = size_4p_records[-1]
        stats_lines.append(f"\nInferential contrast (H6: N=7 vs N=12 4P Seat 0 Win Rate):")
        stats_lines.append(f"  N=7:  {n7_rec[2]}/{n7_rec[1]} ({n7_rec[2]/n7_rec[1]*100:.1f}%)")
        stats_lines.append(f"  N=12: {n12_rec[2]}/{n12_rec[1]} ({n12_rec[2]/n12_rec[1]*100:.1f}%)")

    # -------------------------------------------------------------------------
    # 7. Ablations A1 to A6
    # -------------------------------------------------------------------------
    stats_lines.append("\n--------------------------------------------------------------------------------")
    stats_lines.append("7. ABLATIONS A1-A6 ANALYSIS")
    stats_lines.append("--------------------------------------------------------------------------------")

    # A1
    a1_file = raw_p / "a1_wall_target_paired.json"
    if a1_file.exists():
        d_a1 = load_json(a1_file)
        stats_lines.append("\nA1: Wall Target Pruning (Leader vs All):")
        s = d_a1.get("summary", {})
        for k, v in s.items():
            w = v["wins"]
            n = v["games_played"]
            wr = v["win_rate"]
            low, high = wilson_interval(w, n)
            p_val = exact_two_sided_binomial_p(w, n, 0.25)
            stats_lines.append(f"  {k:35s}: win_rate={wr*100:.1f}% ({w}/{n}) | mean_rank={v['mean_rank']:.2f}")
            ablation_rows.append({
                "ablation_id": "A1",
                "factor": "wall_target",
                "variant": k,
                "mode": "4P 9x9",
                "games_or_positions": n,
                "metric": "win_rate",
                "value": f"{wr:.4f}",
                "ci_low": f"{low:.4f}",
                "ci_high": f"{high:.4f}",
                "p_value": f"{p_val:.4f}",
                "mean_nodes": "",
                "median_ms": "",
                "agreement_rate": "",
            })

    # A2
    a2_file = raw_p / "a2_paradigm_paired.json"
    if a2_file.exists():
        d_a2 = load_json(a2_file)
        stats_lines.append("\nA2: Search Paradigm (Paranoid vs Maxn):")
        s = d_a2.get("summary", {})
        for k, v in s.items():
            w = v["wins"]
            n = v["games_played"]
            wr = v["win_rate"]
            low, high = wilson_interval(w, n)
            p_val = exact_two_sided_binomial_p(w, n, 0.25)
            stats_lines.append(f"  {k:35s}: win_rate={wr*100:.1f}% ({w}/{n}) | mean_rank={v['mean_rank']:.2f}")
            ablation_rows.append({
                "ablation_id": "A2",
                "factor": "search_paradigm",
                "variant": k,
                "mode": "4P 9x9",
                "games_or_positions": n,
                "metric": "win_rate",
                "value": f"{wr:.4f}",
                "ci_low": f"{low:.4f}",
                "ci_high": f"{high:.4f}",
                "p_value": f"{p_val:.4f}",
                "mean_nodes": "",
                "median_ms": "",
                "agreement_rate": "",
            })

    # A3
    a3_file = raw_p / "a3_position_benchmark.json"
    if a3_file.exists():
        d_a3 = load_json(a3_file)
        stats_lines.append("\nA3: Search Enhancements Position Benchmark (60 positions):")
        for k, v in d_a3.items():
            stats_lines.append(f"  {k:15s}: mean_nodes={v['mean_nodes']:6.1f} | med_time={v['median_time_s']*1000:6.2f}ms | move_agreement={v['agreement_rate']*100:.1f}%")
            ablation_rows.append({
                "ablation_id": "A3",
                "factor": "search_enhancements",
                "variant": k,
                "mode": "4P 9x9 Benchmark",
                "games_or_positions": v["positions_tested"],
                "metric": "move_agreement",
                "value": f"{v['agreement_rate']:.4f}",
                "ci_low": "",
                "ci_high": "",
                "p_value": "",
                "mean_nodes": f"{v['mean_nodes']:.1f}",
                "median_ms": f"{v['median_time_s']*1000:.2f}",
                "agreement_rate": f"{v['agreement_rate']:.4f}",
            })

    # A4
    a4_file = raw_p / "a4_eval_mode_paired.json"
    if a4_file.exists():
        d_a4 = load_json(a4_file)
        stats_lines.append("\nA4: Evaluation Function (Leader vs Mean):")
        s = d_a4.get("summary", {})
        for k, v in s.items():
            w = v["wins"]
            n = v["games_played"]
            wr = v["win_rate"]
            low, high = wilson_interval(w, n)
            p_val = exact_two_sided_binomial_p(w, n, 0.25)
            stats_lines.append(f"  {k:35s}: win_rate={wr*100:.1f}% ({w}/{n}) | mean_rank={v['mean_rank']:.2f}")
            ablation_rows.append({
                "ablation_id": "A4",
                "factor": "eval_mode",
                "variant": k,
                "mode": "4P 9x9",
                "games_or_positions": n,
                "metric": "win_rate",
                "value": f"{wr:.4f}",
                "ci_low": f"{low:.4f}",
                "ci_high": f"{high:.4f}",
                "p_value": f"{p_val:.4f}",
                "mean_nodes": "",
                "median_ms": "",
                "agreement_rate": "",
            })

    # A5
    a5_3 = raw_p / "a5_walls_3.json"
    a5_10 = raw_p / "a5_walls_10.json"
    if a5_3.exists() and a5_10.exists():
        d3 = load_json(a5_3)
        d10 = load_json(a5_10)
        pl3 = sum(g['plies'] for g in d3.get('games', [])) / max(1, len(d3.get('games', [])))
        pl10 = sum(g['plies'] for g in d10.get('games', [])) / max(1, len(d10.get('games', [])))
        stats_lines.append("\nA5: Wall Inventory Sensitivity (3 walls vs 10 walls):")
        stats_lines.append(f"  3 walls:  mean_plies = {pl3:.1f}")
        stats_lines.append(f"  10 walls: mean_plies = {pl10:.1f}")
        for label, d_walls, pl in [("walls_3", d3, pl3), ("walls_10", d10, pl10)]:
            s = d_walls.get("summary", {})
            for k, v in s.items():
                w = v["wins"]
                n = v["games_played"]
                wr = v["win_rate"]
                low, high = wilson_interval(w, n)
                p_val = exact_two_sided_binomial_p(w, n, 0.25)
                ablation_rows.append({
                    "ablation_id": f"A5_{label}",
                    "factor": f"wall_inventory_{label}",
                    "variant": k,
                    "mode": "4P 9x9",
                    "games_or_positions": n,
                    "metric": "win_rate",
                    "value": f"{wr:.4f}",
                    "ci_low": f"{low:.4f}",
                    "ci_high": f"{high:.4f}",
                    "p_value": f"{p_val:.4f}",
                    "mean_nodes": "",
                    "median_ms": "",
                    "agreement_rate": "",
                })

    # A6
    a6_file = raw_p / "a6_mcts_rollout_paired.json"
    if a6_file.exists():
        d_a6 = load_json(a6_file)
        stats_lines.append("\nA6: MCTS Rollout Strategy (Path-Biased vs Random):")
        s = d_a6.get("summary", {})
        for k, v in s.items():
            w = v["wins"]
            n = v["games_played"]
            wr = v["win_rate"]
            low, high = wilson_interval(w, n)
            p_val = exact_two_sided_binomial_p(w, n, 0.25)
            stats_lines.append(f"  {k:45s}: win_rate={wr*100:.1f}% ({w}/{n}) | mean_rank={v['mean_rank']:.2f}")
            ablation_rows.append({
                "ablation_id": "A6",
                "factor": "mcts_rollout",
                "variant": k,
                "mode": "4P 9x9",
                "games_or_positions": n,
                "metric": "win_rate",
                "value": f"{wr:.4f}",
                "ci_low": f"{low:.4f}",
                "ci_high": f"{high:.4f}",
                "p_value": f"{p_val:.4f}",
                "mean_nodes": "",
                "median_ms": "",
                "agreement_rate": "",
            })

    # -------------------------------------------------------------------------
    # 8. Write CSVs and Text Report
    # -------------------------------------------------------------------------
    # summary.csv
    summary_path = res_p / "summary.csv"
    if summary_rows:
        fieldnames = list(summary_rows[0].keys())
        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_rows)

    # ablation.csv
    ablation_path = res_p / "ablation.csv"
    if ablation_rows:
        fieldnames = list(ablation_rows[0].keys())
        with open(ablation_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(ablation_rows)

    # stats_n.txt
    stats_path = res_p / "stats_n.txt"
    with open(stats_path, "w", encoding="utf-8") as f:
        f.write("\n".join(stats_lines) + "\n")

    print(f"Analysis written to {summary_path} and {stats_path}")

    # -------------------------------------------------------------------------
    # 9. Generate Publication Figures
    # -------------------------------------------------------------------------
    _generate_figures(fig_p, e2_file, e4_file, raw_p, size_2p_records, size_4p_records)


def _generate_figures(
    fig_dir: Path,
    e2_file: Path,
    e4_file: Path,
    raw_p: Path,
    size_2p: list,
    size_4p: list,
) -> None:
    # 1. E2 Round Robin Win Rates
    if e2_file.exists():
        d = load_json(e2_file)
        summary = d.get("summary", {})
        agents = [sp.split(":")[0] for sp in summary.keys()]
        win_rates = [s["win_rate"] * 100 for s in summary.values()]
        cis = [
            (
                (s["win_rate"] - wilson_interval(s["wins"], s["games_played"])[0]) * 100,
                (wilson_interval(s["wins"], s["games_played"])[1] - s["win_rate"]) * 100,
            )
            for s in summary.values()
        ]
        yerr = np.array(cis).T

        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar(agents, win_rates, yerr=yerr, capsize=4, color=["#858383", "#E5532D", "#C05621", "#2E4BDB"])
        ax.axhline(25, color="black", linestyle="--", linewidth=1, label="Chance (25%)")
        ax.set_ylabel("Win Rate (%)")
        ax.set_title("E2: 4-Player Round-Robin Win Rates (9x9, 168 games)")
        ax.set_ylim(0, 70)
        ax.legend()
        fig.tight_layout()
        fig.savefig(fig_dir / "e2_round_robin.png", dpi=200)
        plt.close(fig)

    # 2. E5 Board Size Scaling
    if size_2p and size_4p:
        fig, ax1 = plt.subplots(figsize=(6, 4))
        sizes_2 = [r[0] for r in size_2p]
        plies_2 = [r[3] for r in size_2p]
        sizes_4 = [r[0] for r in size_4p]
        plies_4 = [r[3] for r in size_4p]

        ax1.plot(sizes_2, plies_2, "o-", color="#2E4BDB", label="2-Player Game Length")
        ax1.plot(sizes_4, plies_4, "s--", color="#E5532D", label="4-Player Game Length")
        ax1.set_xlabel("Board Size N")
        ax1.set_ylabel("Mean Game Plies")
        ax1.set_title("E5: Game Length vs Board Dimension N in [7, 12]")
        ax1.grid(True, linestyle=":", alpha=0.6)
        ax1.legend()
        fig.tight_layout()
        fig.savefig(fig_dir / "e5_board_size.png", dpi=200)
        plt.close(fig)

    # 3. Seat Effect by Size
    if size_4p:
        fig, ax = plt.subplots(figsize=(6, 4))
        sizes = [r[0] for r in size_4p]
        s0_rates = [(r[2] / max(1, r[1])) * 100 for r in size_4p]
        cis = [
            (
                (r[2] / r[1] - wilson_interval(r[2], r[1])[0]) * 100,
                (wilson_interval(r[2], r[1])[1] - r[2] / r[1]) * 100,
            )
            for r in size_4p
        ]
        yerr = np.array(cis).T
        ax.errorbar(sizes, s0_rates, yerr=yerr, fmt="o-", color="#E5532D", capsize=4, label="Seat 0 Win Rate")
        ax.axhline(25, color="black", linestyle="--", linewidth=1, label="Chance (25%)")
        ax.set_xlabel("Board Size N")
        ax.set_ylabel("Win Rate (%)")
        ax.set_title("Seat 0 Advantage across Board Dimension N")
        ax.set_ylim(0, 60)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend()
        fig.tight_layout()
        fig.savefig(fig_dir / "seat_effect_by_size.png", dpi=200)
        plt.close(fig)

    # 4. E4 Leader Targeting vs Placebo
    if e4_file.exists():
        e4_d = load_json(e4_file)
        tw = e4_d["total_walls"]
        ld = e4_d["total_leader_delayed"]
        ph = e4_d["total_placebo_hits"]
        pc = e4_d["total_placebo_candidates"]

        r_target = (ld / max(1, tw)) * 100
        r_placebo = (ph / max(1, pc)) * 100

        ci_t = wilson_interval(ld, tw)
        ci_p = wilson_interval(ph, pc)
        yerr_t = [(r_target - ci_t[0] * 100), (ci_t[1] * 100 - r_target)]
        yerr_p = [(r_placebo - ci_p[0] * 100), (ci_p[1] * 100 - r_placebo)]

        fig, ax = plt.subplots(figsize=(5, 4))
        bars = ax.bar(
            ["Agent Wall Placements", "Random Placebo Baseline"],
            [r_target, r_placebo],
            yerr=np.array([yerr_t, yerr_p]).T,
            capsize=4,
            color=["#2E4BDB", "#858383"],
        )
        ax.set_ylabel("% Lengthening Leader Path")
        ax.set_title("E4: Leader Targeting vs Placebo Baseline")
        ax.set_ylim(0, 80)
        fig.tight_layout()
        fig.savefig(fig_dir / "e4_targeting.png", dpi=200)
        plt.close(fig)

    # 5. Paired Ablations (A1, A2, A4)
    a1_f = raw_p / "a1_wall_target_paired.json"
    a2_f = raw_p / "a2_paradigm_paired.json"
    a4_f = raw_p / "a4_eval_mode_paired.json"
    if a1_f.exists() and a2_f.exists() and a4_f.exists():
        fig, axes = plt.subplots(1, 3, figsize=(11, 3.5), sharey=True)
        pairs = [
            (axes[0], a1_f, "A1: Wall Target", ["all", "leader"]),
            (axes[1], a2_f, "A2: Paradigm", ["paranoid", "maxn"]),
            (axes[2], a4_f, "A4: Eval Mode", ["mean", "leader"]),
        ]
        for ax, fp, title, labels in pairs:
            d_ab = load_json(fp)
            s_ab = d_ab.get("summary", {})
            keys = [k for k in s_ab.keys() if any(lb in k for lb in labels)]
            rates = [s_ab[k]["win_rate"] * 100 for k in keys]
            short_lbls = [k.split(":")[0] + ("-" + k.split("=")[1] if "=" in k else "") for k in keys]
            ax.bar(short_lbls, rates, color=["#2E4BDB", "#E5532D"])
            ax.axhline(25, color="black", linestyle="--", linewidth=0.8)
            ax.set_title(title, fontsize=10)
            ax.set_ylim(0, 50)
            ax.grid(True, linestyle=":", alpha=0.5)
        axes[0].set_ylabel("Win Rate (%)")
        fig.tight_layout()
        fig.savefig(fig_dir / "paired_ablations.png", dpi=200)
        plt.close(fig)

    # 6. Board Geometry Diagrams
    _generate_board_diagrams(fig_dir)


def _generate_board_diagrams(fig_dir: Path) -> None:
    """Diagram showing start cells and goal sides for 7x7 and 12x12."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4.5))

    for ax, n in [(ax1, 7), (ax2, 12)]:
        ax.set_xlim(-1, n)
        ax.set_ylim(-1, n)
        ax.set_aspect("equal")
        ax.invert_yaxis()

        # Grid lines
        for r in range(n + 1):
            ax.axhline(r - 0.5, color="#D9D7D0", linewidth=0.8)
        for c in range(n + 1):
            ax.axvline(c - 0.5, color="#D9D7D0", linewidth=0.8)

        # Goal sides
        # Seat 0 goal: top row 0
        ax.axhline(-0.5, color="#2E4BDB", linewidth=3, label="Seat 0 Goal" if ax == ax1 else "")
        # Seat 2 goal: bottom row n-1
        ax.axhline(n - 0.5, color="#E5532D", linewidth=3, label="Seat 2 Goal" if ax == ax1 else "")
        # Seat 1 goal: right col n-1
        ax.axvline(n - 0.5, color="#C05621", linewidth=3, label="Seat 1 Goal" if ax == ax1 else "")
        # Seat 3 goal: left col 0
        ax.axvline(-0.5, color="#7C3AED", linewidth=3, label="Seat 3 Goal" if ax == ax1 else "")

        # Start cells
        c0 = (n - 1) // 2
        ax.plot(c0, n - 1, "o", color="#2E4BDB", markersize=10, label="Seat 0 Start" if ax == ax1 else "")
        ax.plot(0, c0, "^", color="#C05621", markersize=10, label="Seat 1 Start" if ax == ax1 else "")
        ax.plot(n - 1 - c0, 0, "s", color="#E5532D", markersize=9, label="Seat 2 Start" if ax == ax1 else "")
        ax.plot(n - 1, n - 1 - c0, "D", color="#7C3AED", markersize=9, label="Seat 3 Start" if ax == ax1 else "")

        ax.set_title(f"{n}x{n} Board (Start & Goals)")
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(range(n))
        ax.set_yticklabels(range(n))

    ax1.legend(loc="upper center", bbox_to_anchor=(1.1, -0.15), ncol=4, frameon=False)
    fig.tight_layout()
    fig.savefig(fig_dir / "board_diagram.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    analyze_all()
