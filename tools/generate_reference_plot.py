import math
from pathlib import Path

import matplotlib.pyplot as plt

DEFAULT_TARGET_PERCENT = 0.20
MIN_TARGET_SOLVES = 5


def smoothstep(progress):
    progress = max(0.0, min(1.0, progress))
    return progress * progress * (3.0 - (2.0 * progress))


def calculate_effective_field(registered_teams, active_teams):
    registered = max(1, int(registered_teams))
    active = max(1, int(active_teams))
    blended = int(round((registered * active) ** 0.5))
    return max(active, min(registered, blended))


def calculate_target_solves(initial, minimum, target_percent, effective_field):
    span = max(0, int(round(initial)) - int(round(minimum)))
    if span <= 0:
        return 1

    percent_target = int(
        math.ceil(max(0.05, min(float(target_percent), 1.0)) * effective_field)
    )
    target_solves = max(min(MIN_TARGET_SOLVES, effective_field), percent_target)
    return min(target_solves, effective_field, span)


def build_ladder(initial, minimum, target_percent, registered_teams, active_teams):
    effective_field = calculate_effective_field(registered_teams, active_teams)
    target_solves = calculate_target_solves(
        initial, minimum, target_percent, effective_field
    )

    ladder = [int(round(initial))]
    previous = ladder[0]

    for solves_before in range(1, registered_teams + 1):
        remaining = 1.0 - smoothstep(float(solves_before) / max(target_solves, 1))
        raw_value = float(minimum) + ((float(initial) - float(minimum)) * remaining)
        value = int(round(raw_value))
        value = max(int(round(minimum)), min(int(round(initial)), value))
        if previous > int(round(minimum)):
            value = min(value, previous - 1)
        value = max(int(round(minimum)), value)
        ladder.append(value)
        previous = value

    return effective_field, target_solves, ladder


def main():
    scenarios = [
        {
            "registered": 20,
            "active": 20,
            "label": "20 registered / 20 active",
            "color": "#c47a1c",
        },
        {
            "registered": 100,
            "active": 60,
            "label": "100 registered / 60 active",
            "color": "#2e86ab",
        },
        {
            "registered": 300,
            "active": 180,
            "label": "300 registered / 180 active",
            "color": "#9b2226",
        },
    ]

    initial = 500
    minimum = 100
    target_percent = DEFAULT_TARGET_PERCENT

    fig, ax = plt.subplots(figsize=(10, 6))

    for scenario in scenarios:
        effective_field, target_solves, ladder = build_ladder(
            initial=initial,
            minimum=minimum,
            target_percent=target_percent,
            registered_teams=scenario["registered"],
            active_teams=scenario["active"],
        )
        x_values = list(range(len(ladder)))
        ax.plot(
            x_values,
            ladder,
            label=(
                f"{scenario['label']}  effective={effective_field}"
                f"  floor@{target_solves} solves"
            ),
            color=scenario["color"],
            linewidth=2.5,
        )
        ax.axvline(
            target_solves,
            color=scenario["color"],
            linestyle="--",
            linewidth=1,
            alpha=0.35,
        )

    ax.set_title("Percentage-Based Dynamic Score Reference Curve")
    ax.set_xlabel("Solves Before Current Team")
    ax.set_ylabel("Score Awarded")
    ax.set_xlim(left=0)
    ax.set_ylim(minimum - 10, initial + 20)
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)

    output_path = Path(__file__).resolve().parents[1] / "docs" / "reference_curve.svg"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, format="svg")


if __name__ == "__main__":
    main()
