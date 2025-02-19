import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from bench.cost import cheapest_eligible, cost_per_1000


def main():
    p = argparse.ArgumentParser()
    p.add_argument("runs", nargs="+", type=Path)
    p.add_argument("--tariffs", type=Path, default=Path("configs/tariffs.json"))
    p.add_argument("--billing", type=Path, help="JSON indexed by model; required for cloud costs")
    p.add_argument("--threshold", type=float, default=0.6)
    p.add_argument("--out", type=Path, default=Path("report/results"))
    a = p.parse_args()
    tariffs = json.loads(a.tariffs.read_text())["tariffs"]
    billing = json.loads(a.billing.read_text()) if a.billing else {}
    groups = defaultdict(list)
    for path in a.runs:
        for line in path.read_text().splitlines():
            row = json.loads(line)
            groups[(row["model"], row["run_id"], row["language"], row["task"])].append(row)
    summaries = []
    for (model, run, language, task), attempts in groups.items():
        rows = list({r["id"]: r for r in attempts}.values())
        good = [r for r in rows if r["status"] == "ok"]
        summary = {
            "model": model,
            "run_id": run,
            "language": language,
            "task": task,
            "n": len(rows),
            "successful_requests": len(good),
            "attempts_including_retries": len(attempts),
            "partial": any(r.get("partial", False) for r in rows),
            "accuracy": sum(r.get("correct", False) for r in rows) / len(rows),
            "error_rate": 1 - len(good) / len(rows),
            "median_latency_seconds": statistics.median(r["end_to_end_seconds"] for r in rows),
        }
        if not good:
            summaries.append({**summary, "tariff": None, "cost_ngn": None})
            continue
        for field in [
            "time_to_first_text_seconds",
            "time_to_first_word_seconds",
            "words_per_second",
        ]:
            values = [r[field] for r in good if r.get(field) is not None]
            summary["median_" + field] = statistics.median(values) if values else None
        memory = [
            r["peak_server_rss_bytes_sampled"]
            for r in good
            if r.get("peak_server_rss_bytes_sampled") is not None
        ]
        summary["peak_server_rss_bytes_sampled"] = max(memory) if memory else None
        bytes_known = all("mb_per_question" in r for r in attempts)
        mb = sum(r.get("mb_per_question", 0) for r in attempts) / len(rows)
        for tariff in tariffs:
            prices = billing.get(model, {})
            try:
                token_rows = [r["usage"] for r in attempts if r.get("usage")]
                usage = (
                    {
                        key: sum(r[key] for r in token_rows) / len(rows)
                        for key in ["prompt_tokens", "completion_tokens"]
                    }
                    if len(token_rows) == len(attempts)
                    else None
                )
                if not bytes_known:
                    raise ValueError("Missing byte accounting for at least one attempt")
                values = cost_per_1000(
                    placement=rows[0]["placement"],
                    mb_per_question=mb,
                    ngn_per_mb=tariff["ngn_per_mb"],
                    usage=usage,
                    **prices,
                )
                cost = values["total_ngn"]
            except ValueError:
                cost = None
            summaries.append(
                {
                    **summary,
                    "tariff": tariff["id"],
                    "cost_ngn": cost,
                    "mb_per_question": mb,
                    "cost_note": "Per 1,000 unique questions including observed retry payloads; warmups, download and transport overhead excluded",
                }
            )
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps(summaries, indent=2))
    fields = sorted(set().union(*(r.keys() for r in summaries)))
    with (a.out / "summary.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(summaries)
    decisions = []
    for language, task, tariff in sorted(
        {(r["language"], r["task"], r["tariff"]) for r in summaries}
    ):
        choice = cheapest_eligible(
            [
                r
                for r in summaries
                if not r["partial"]
                and (r["language"], r["task"], r["tariff"]) == (language, task, tariff)
            ],
            a.threshold,
        )
        decisions.append(
            {
                "language": language,
                "task": task,
                "tariff": tariff,
                "threshold": a.threshold,
                "choice": choice,
            }
        )
    (a.out / "decisions.json").write_text(json.dumps(decisions, indent=2))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = {"yor": "#2563eb", "hau": "#d97706", "ibo": "#059669", "eng": "#6b7280"}
    for row in summaries:
        if row.get("cost_ngn") is None:
            continue
        ax.scatter(row["cost_ngn"], row["accuracy"] * 100, c=colors[row["language"]])
    ax.set(
        xlabel="NGN per 1,000 questions (marginal)",
        ylabel="Accuracy (%)",
        title="Phone or cloud? Measured accuracy and cost",
    )
    if any(row.get("partial") for row in summaries):
        ax.set_title("Exploratory local pilot; full phone/cloud benchmarks pending")
    from matplotlib.lines import Line2D

    ax.legend(
        handles=[
            Line2D(
                [0], [0], marker="o", color="w", markerfacecolor=color, label=language, markersize=7
            )
            for language, color in colors.items()
        ]
    )
    fig.tight_layout()
    fig.savefig(a.out / "accuracy-cost.png", dpi=180)


if __name__ == "__main__":
    main()
