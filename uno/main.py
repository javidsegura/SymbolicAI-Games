import sys
from pathlib import Path
from typing import List, Tuple

from uno import local_engine

AGENTS: List[Tuple[str, str]] = [
    ("Monte Carlo", "uno.agents.monte_carlo:monte_carlo_agent"),
    ("Priority Greedy", "uno.agents.priority_queue:priority_queue_agent"),
    ("IDDFS", "uno.agents.iddfs:iddfs_agent"),
    ("Baseline Heuristic", "uno.my_agents:my_agent"),
]


def ensure_project_root():
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def run_rotation(agent_order: List[Tuple[str, str]], num_games: int) -> dict:
    specs = [spec for _, spec in agent_order]
    return local_engine.run_parallel_games(
        agent_specs=specs,
        num_games=num_games,
        processes=8,
        config=local_engine.LocalUnoConfig(max_turns=400),
    )


def aggregate_showdown(rounds: int = None, games_per_round: int = 400):
    rounds = rounds or len(AGENTS)
    aggregate = {name: {"wins": 0, "games": 0} for name, _ in AGENTS}

    for offset in range(rounds):
        order = AGENTS[offset:] + AGENTS[:offset]
        stats = run_rotation(order, games_per_round)

        print(f"\n=== Rotation {offset + 1} ===")
        for idx, (name, _) in enumerate(order):
            player_id = f"P{idx + 1}"
            wins = stats["per_player"][player_id]["wins"]
            win_rate = stats["per_player"][player_id]["win_rate"] * 100
            print(f"{name:18s} -> seat {player_id}, wins {wins}, win rate {win_rate:.1f}%")
            aggregate[name]["wins"] += wins
            aggregate[name]["games"] += games_per_round

        print(f"Draws: {stats['draws']} | Avg turns: {stats['avg_turns']:.1f}")

    print("\n=== Overall Results ===")
    for name, data in aggregate.items():
        total_games = data["games"]
        total_wins = data["wins"]
        win_rate = (total_wins / total_games) * 100 if total_games else 0.0
        print(f"{name:18s}: {total_wins} wins / {total_games} games -> {win_rate:.2f}%")


def main():
    ensure_project_root()
    aggregate_showdown()


if __name__ == "__main__":
    main()

