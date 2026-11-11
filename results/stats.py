"""Compute 95% Wilson confidence intervals and exact binomial two-sided p-values."""
from __future__ import annotations

import csv
import math
from pathlib import Path


def wilson_interval(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Calculate the Wilson score confidence interval for a binomial proportion."""
    if n == 0:
        return 0.0, 0.0
    # For 95% confidence, z ~ 1.95996398454
    z = 1.959963984540054
    z2 = z * z
    p_hat = k / n
    denominator = 1 + z2 / n
    centre_adj = p_hat + z2 / (2 * n)
    margin = z * math.sqrt((p_hat * (1 - p_hat) / n) + (z2 / (4 * n * n)))
    lower = max(0.0, (centre_adj - margin) / denominator)
    upper = min(1.0, (centre_adj + margin) / denominator)
    return lower, upper


def binomial_pmf(k: int, n: int, p: float = 0.5) -> float:
    """Exact binomial probability mass function."""
    return math.comb(n, k) * (p**k) * ((1.0 - p) ** (n - k))


def exact_two_sided_binomial_p(k: int, n: int, p0: float = 0.5) -> float:
    """Exact two-sided binomial p-value testing H0: p = p0."""
    if n == 0:
        return 1.0
    pk = binomial_pmf(k, n, p0)
    # Sum probabilities of all outcomes with probability <= pk (within float tolerance)
    total_p = 0.0
    eps = 1e-12
    for j in range(n + 1):
        pj = binomial_pmf(j, n, p0)
        if pj <= pk + eps:
            total_p += pj
    return min(1.0, total_p)


def main() -> None:
    csv_path = Path(__file__).resolve().parent / "summary.csv"
    txt_path = Path(__file__).resolve().parent / "stats.txt"

    lines = []
    header = f"{'Matchup':<32} | {'Score':<8} | {'Win %':<8} | {'95% Wilson CI':<18} | {'p-value (vs 50%)'}"
    div = "-" * 88
    lines.append(header)
    lines.append(div)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pair = row["pair"]
            n = int(row["games"])
            wins_a = int(row["wins_a"])
            low, high = wilson_interval(wins_a, n)
            p_val = exact_two_sided_binomial_p(wins_a, n, 0.5)

            score_str = f"{wins_a}/{n}"
            win_str = f"{(wins_a / n) * 100:.1f}%"
            ci_str = f"[{low * 100:.1f}%, {high * 100:.1f}%]"
            p_str = f"{p_val:.4f}"

            lines.append(f"{pair:<32} | {score_str:<8} | {win_str:<8} | {ci_str:<18} | {p_str}")

    output_text = "\n".join(lines) + "\n"
    print(output_text)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(output_text)
    print(f"Saved stats to {txt_path}")


if __name__ == "__main__":
    main()
