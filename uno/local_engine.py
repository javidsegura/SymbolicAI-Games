"""Local UNO simulation engine with parallel execution helpers.

This module lets you pit UNO agents against each other without having to hit
the remote evaluation server.  It contains a lightweight rules engine plus a
ProcessPoolExecutor-powered runner so you can benchmark thousands of games in
seconds on your local machine.

Typical usage from a notebook or script:

>>> from uno import local_engine
>>> result = local_engine.run_parallel_games(
...     agent_specs="uno.agents:my_agent",  # module:function import path
...     num_games=1000,
...     processes=8,
... )
>>> result["per_player"]["P1"]["win_rate"]

If you want to experiment quickly inside the notebook without creating a
module for your agent yet, you can also call `simulate_games` directly with an
in-memory callable (single-process, so pickle issues disappear).
"""

from __future__ import annotations

import importlib
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

Card = Dict[str, Any]
Move = Dict[str, Any]
AgentFn = Callable[["UnoGameView"], Move]
AgentSpec = Union[str, AgentFn]

COLORS = ["red", "blue", "green", "yellow"]
NUMBER_VALUES = [str(n) for n in range(10)]
ACTION_VALUES = ["skip", "reverse", "draw2"]
WILD_VALUES = ["wild", "wild_draw4"]


@dataclass
class LocalUnoConfig:
    """Configuration knobs for the local UNO simulator."""

    num_players: int = 4
    starting_hand_size: int = 7
    max_turns: int = 500
    allow_draw_when_playable: bool = True
    reshuffle_discard: bool = True
    verbose: bool = False


@dataclass
class GameResult:
    """Outcome of a single simulated UNO game."""

    winner: Optional[str]
    turns: int
    remaining_cards: Dict[str, int]
    reason: str
    seed: int


class _DeckEmptyError(RuntimeError):
    """Raised when no further draws are possible."""


def run_parallel_games(
    agent_specs: Union[AgentSpec, Sequence[AgentSpec]],
    num_games: int,
    *,
    config: Optional[LocalUnoConfig] = None,
    processes: Optional[int] = None,
    base_seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Run many UNO games in parallel using ProcessPoolExecutor.

    Args:
        agent_specs: Either a single spec (string "module:function" or callable)
            to clone across every seat, or a sequence whose length matches
            `config.num_players`.  When running in multiple processes, prefer
            the string form so the worker can import your agent without needing
            cloudpickle.
        num_games: Total games to simulate.
        config: Optional LocalUnoConfig overrides.
        processes: Max worker processes (defaults to os.cpu_count()).
        base_seed: Optional seed to deterministically derive per-game seeds.

    Returns:
        Dictionary with aggregate statistics (`per_player`, `draws`,
        `avg_turns`, `results` list, etc.).
    """

    if num_games <= 0:
        raise ValueError("num_games must be > 0")

    config = config or LocalUnoConfig()
    specs = _normalize_agent_specs(agent_specs, config.num_players)
    seeds = _generate_seeds(num_games, base_seed)

    payloads = [(specs, config, seed) for seed in seeds]
    results: List[GameResult] = []

    with ProcessPoolExecutor(max_workers=processes) as executor:
        futures = [executor.submit(_worker_play_game, payload) for payload in payloads]
        for fut in as_completed(futures):
            results.append(fut.result())

    return _summarize_results(results, config)


def simulate_games(
    agent_factories: Union[AgentFn, Sequence[AgentFn]],
    num_games: int,
    *,
    config: Optional[LocalUnoConfig] = None,
    base_seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Single-process fallback that accepts raw callables (helpful in notebooks)."""

    config = config or LocalUnoConfig()
    agents = _normalize_agent_specs(agent_factories, config.num_players)
    seeds = _generate_seeds(num_games, base_seed)
    results = []
    for seed in seeds:
        fn_list = [_resolve_agent(spec) for spec in agents]
        sim = _LocalUnoSimulator(config=config, seed=seed)
        results.append(sim.play_game(fn_list))
    return _summarize_results(results, config)


def _worker_play_game(args: Tuple[Sequence[AgentSpec], LocalUnoConfig, int]) -> GameResult:
    specs, config, seed = args
    agent_fns = [_resolve_agent(spec) for spec in specs]
    simulator = _LocalUnoSimulator(config=config, seed=seed)
    return simulator.play_game(agent_fns)


def _normalize_agent_specs(
    specs: Union[AgentSpec, Sequence[AgentSpec]],
    num_players: int,
) -> List[AgentSpec]:
    if isinstance(specs, (list, tuple)):
        if len(specs) != num_players:
            raise ValueError(f"Expected {num_players} agent specs, got {len(specs)}")
        return list(specs)
    return [specs for _ in range(num_players)]


def _generate_seeds(num_games: int, base_seed: Optional[int]) -> List[int]:
    rng = random.Random(base_seed)
    return [rng.randrange(1 << 30) for _ in range(num_games)]


def _resolve_agent(spec: AgentSpec) -> AgentFn:
    if callable(spec):
        return spec
    if not isinstance(spec, str):
        raise TypeError(f"Agent spec must be callable or 'module:function', got {type(spec)}")
    if ":" not in spec:
        raise ValueError("String agent specs must look like 'package.module:function'")
    module_path, fn_name = spec.split(":", 1)
    module = importlib.import_module(module_path)
    fn = getattr(module, fn_name)
    if not callable(fn):
        raise TypeError(f"{spec} did not resolve to a callable")
    return fn


def _summarize_results(results: List[GameResult], config: LocalUnoConfig) -> Dict[str, Any]:
    per_player = {f"P{i+1}": {"wins": 0, "win_rate": 0.0, "avg_remaining": 0.0} for i in range(config.num_players)}
    draws = 0
    total_turns = 0

    for res in results:
        total_turns += res.turns
        if res.winner:
            per_player[res.winner]["wins"] += 1
        else:
            draws += 1
        for pid, remaining in res.remaining_cards.items():
            per_player[pid]["avg_remaining"] += remaining

    total_games = len(results)
    for stats in per_player.values():
        stats["win_rate"] = stats["wins"] / total_games if total_games else 0.0
        stats["avg_remaining"] = stats["avg_remaining"] / total_games if total_games else 0.0

    return {
        "per_player": per_player,
        "draws": draws,
        "avg_turns": total_turns / total_games if total_games else 0.0,
        "results": results,
    }


class UnoGameView:
    """Read-only perspective on the game state exposed to agents."""

    def __init__(self, state: Dict[str, Any], status: str, current_player: str, my_player: str):
        self._state = state
        self.status = status
        self.current_player = current_player
        self.my_player = my_player

    @property
    def state(self) -> Dict[str, Any]:
        return self._state

    def get_my_hand(self) -> List[Card]:
        return self._state["hands"].get(self.my_player, [])

    def get_hand_sizes(self) -> Dict[str, int]:
        return {player: len(hand) for player, hand in self._state.get("hands", {}).items()}

    def get_current_color(self) -> str:
        return self._state.get("current_color", "")

    def get_top_card(self) -> Dict[str, Any]:
        discard = self._state.get("discard_pile", [])
        return discard[-1] if discard else {}

    def get_discard_pile(self) -> List[Card]:
        return list(self._state.get("discard_pile", []))

    def get_discard_pile_size(self) -> int:
        return len(self._state.get("discard_pile", []))

    def is_terminal(self) -> bool:
        return self.status == "complete"

    def _can_play_card(self, card: Card, top_card: Card, current_color: str) -> bool:
        if not top_card:
            return True
        if card.get("type") == "wild":
            return True
        if card.get("color") == current_color:
            return True
        if card.get("value") == top_card.get("value"):
            return True
        return False

    def get_valid_moves(self) -> List[Move]:
        if self.current_player != self.my_player:
            return []

        hand = self.get_my_hand()
        top_card = self.get_top_card()
        current_color = self.get_current_color()
        valid_moves: List[Move] = []

        for idx, card in enumerate(hand):
            if self._can_play_card(card, top_card, current_color):
                move = {
                    "type": "play",
                    "card_index": idx,
                    "card": card,
                    "call_uno": len(hand) == 2,
                }
                if card.get("type") == "wild":
                    for color in COLORS:
                        colored_move = dict(move)
                        colored_move["color_choice"] = color
                        valid_moves.append(colored_move)
                else:
                    valid_moves.append(move)

        valid_moves.append({"type": "draw", "count": 1})
        return valid_moves

    def print_state(self) -> None:
        print("\n" + "=" * 40)
        print(f"Current Turn: {self.current_player}")
        print(f"Current Color: {self.get_current_color().upper()}")
        top_card = self.get_top_card()
        if top_card:
            print(f"Top Card: {top_card.get('color')} {top_card.get('value')}")
        print("\nHand Sizes:")
        for player, size in sorted(self.get_hand_sizes().items()):
            if player != self.my_player:
                print(f"  {player}: {size} cards")
        my_hand = self.get_my_hand()
        print(f"\nYour Hand ({len(my_hand)} cards):")
        for idx, card in enumerate(my_hand):
            print(f"  {idx}: {card.get('color')} {card.get('value')}")
        print("=" * 40)


class _LocalUnoSimulator:
    """Stateful UNO rules engine used internally by the runners."""

    def __init__(self, config: LocalUnoConfig, seed: int):
        self.config = config
        self.seed = seed
        self.rng = random.Random(seed)
        self.player_ids = [f"P{i+1}" for i in range(config.num_players)]
        self.direction = 1
        self.current_idx = 0
        self._deck = self._init_deck()
        self._hands = {pid: [self._deck.pop() for _ in range(config.starting_hand_size)] for pid in self.player_ids}
        self._discard_pile: List[Card] = []
        self._init_discard()
        self.current_color = self._discard_pile[-1]["color"]

    def play_game(self, agent_fns: Sequence[AgentFn]) -> GameResult:
        turns = 0
        winner: Optional[str] = None
        reason = "max_turns"

        try:
            while turns < self.config.max_turns:
                current_player = self.player_ids[self.current_idx]
                view = self._build_view(current_player)
                agent = agent_fns[self.current_idx]
                move = self._safe_call_agent(agent, view)
                self._apply_move(move, current_player)

                if not self._hands[current_player]:
                    winner = current_player
                    reason = "win"
                    break

                turns += 1
        except _DeckEmptyError:
            reason = "deck_empty"

        remaining = {pid: len(hand) for pid, hand in self._hands.items()}
        return GameResult(winner=winner, turns=turns, remaining_cards=remaining, reason=reason, seed=self.seed)

    # ---- setup helpers -------------------------------------------------

    def _init_deck(self) -> List[Card]:
        deck: List[Card] = []
        for color in COLORS:
            deck.append({"color": color, "value": "0", "type": "normal"})
            for value in NUMBER_VALUES[1:]:
                for _ in range(2):
                    deck.append({"color": color, "value": value, "type": "normal"})
            for action in ACTION_VALUES:
                for _ in range(2):
                    deck.append({"color": color, "value": action, "type": "action"})
        for wild in WILD_VALUES:
            for _ in range(4):
                deck.append({"color": "wild", "value": wild, "type": "wild"})
        self.rng.shuffle(deck)
        return deck

    def _init_discard(self) -> None:
        while self._deck:
            card = self._deck.pop()
            if card["type"] == "wild":
                self._deck.insert(0, card)
                self.rng.shuffle(self._deck)
                continue
            self._discard_pile.append(card)
            return
        raise RuntimeError("Deck exhausted before initializing discard pile")

    # ---- gameplay helpers ---------------------------------------------

    def _build_view(self, my_player: str) -> UnoGameView:
        public_hands: Dict[str, List[Card]] = {}
        for pid, hand in self._hands.items():
            if pid == my_player:
                public_hands[pid] = list(hand)
            else:
                public_hands[pid] = [{"color": "hidden", "value": "hidden", "type": "hidden"} for _ in hand]

        state = {
            "hands": public_hands,
            "discard_pile": list(self._discard_pile),
            "current_color": self.current_color,
            "current_player": self.player_ids[self.current_idx],
            "draw_pile_size": len(self._deck),
            "turn_direction": self.direction,
        }

        return UnoGameView(state=state, status="in_progress", current_player=self.player_ids[self.current_idx], my_player=my_player)

    def _safe_call_agent(self, agent: AgentFn, view: UnoGameView) -> Move:
        try:
            move = agent(view)
        except Exception as exc:  # pragma: no cover - defensive path
            raise RuntimeError(f"Agent {view.my_player} crashed: {exc}") from exc
        if not isinstance(move, dict):
            raise TypeError(f"Agent must return a move dict, got {type(move)}")
        return move

    def _apply_move(self, move: Move, player: str) -> None:
        move_type = move.get("type")
        if move_type == "draw":
            self._handle_draw(player, count=int(move.get("count", 1)))
            self._advance_player(steps=1)
            return

        if move_type != "play":
            raise ValueError(f"Unknown move type: {move_type}")

        hand = self._hands[player]
        idx = move.get("card_index")
        if not isinstance(idx, int) or not 0 <= idx < len(hand):
            raise ValueError("Invalid card_index in move")

        card = hand[idx]
        top_card = self._discard_pile[-1] if self._discard_pile else {}
        if not self._can_play(card, top_card):
            raise ValueError(f"Illegal card played: {card}")

        hand.pop(idx)
        self._discard_pile.append(card)
        chosen_color = move.get("color_choice")
        if card["type"] == "wild":
            if chosen_color not in COLORS:
                chosen_color = self._auto_choose_color(hand)
            self.current_color = chosen_color
        else:
            self.current_color = card["color"]

        steps = 1
        if card["value"] == "skip":
            steps += 1
        elif card["value"] == "reverse":
            if len(self.player_ids) == 2:
                steps += 1
            else:
                self.direction *= -1
        elif card["value"] == "draw2":
            self._force_draw(self._next_player_index(), 2)
            steps += 1
        elif card["value"] == "wild_draw4":
            self._force_draw(self._next_player_index(), 4)
            steps += 1

        self._advance_player(steps=steps)

    def _handle_draw(self, player: str, count: int) -> None:
        for _ in range(max(1, count)):
            self._hands[player].append(self._draw_card())

    def _force_draw(self, player_index: int, amount: int) -> None:
        target = self.player_ids[player_index]
        for _ in range(amount):
            self._hands[target].append(self._draw_card())

    def _draw_card(self) -> Card:
        if not self._deck:
            if not self.config.reshuffle_discard or len(self._discard_pile) <= 1:
                raise _DeckEmptyError("No cards left to draw")
            top = self._discard_pile.pop()
            self._deck = self._discard_pile
            self.rng.shuffle(self._deck)
            self._discard_pile = [top]
        return self._deck.pop()

    def _advance_player(self, steps: int) -> None:
        self.current_idx = (self.current_idx + steps * self.direction) % len(self.player_ids)

    def _next_player_index(self) -> int:
        return (self.current_idx + self.direction) % len(self.player_ids)

    def _can_play(self, card: Card, top_card: Card) -> bool:
        if not top_card:
            return True
        if card["type"] == "wild":
            return True
        if card["color"] == self.current_color:
            return True
        return card["value"] == top_card.get("value")

    def _auto_choose_color(self, hand: List[Card]) -> str:
        counts = {color: 0 for color in COLORS}
        for card in hand:
            color = card.get("color")
            if color in counts:
                counts[color] += 1
        return max(counts.items(), key=lambda item: item[1])[0]


def random_agent(game: UnoGameView) -> Move:
    """Baseline agent that plays a random valid move."""

    valid = game.get_valid_moves()
    if not valid:
        return {"type": "draw", "count": 1}
    play_moves = [m for m in valid if m["type"] == "play"]
    if play_moves:
        return random.choice(play_moves)
    return random.choice(valid)


__all__ = [
    "LocalUnoConfig",
    "GameResult",
    "UnoGameView",
    "run_parallel_games",
    "simulate_games",
    "random_agent",
]

