import math
from collections import Counter
from copy import deepcopy
from typing import Any, Dict, List, Tuple

Card = Dict[str, Any]
Move = Dict[str, Any]


def iddfs_agent(game: Any, max_depth: int = 3) -> Move:
    """IDDFS with card counting and opponent hand tracking."""

    valid_moves = game.get_valid_moves()
    if not valid_moves:
        return {"type": "draw", "count": 1}

    hand = game.get_my_hand()
    discard_pile = game.get_discard_pile()
    hand_sizes = game.get_hand_sizes()
    card_counts = _count_cards_in_play(hand, discard_pile)

    best_move = None
    best_score = -math.inf

    state = _SearchState(
        hand=deepcopy(hand),
        current_color=game.get_current_color(),
        top_value=game.get_top_card().get("value"),
        card_counts=card_counts,
        hand_sizes=hand_sizes,
        my_player=game.my_player,
    )

    for depth in range(1, max_depth + 1):
        for move in valid_moves:
            score = _dfs(state, move, depth)
            if score > best_score:
                best_score = score
                best_move = move

    return best_move or {"type": "draw", "count": 1}


class _SearchState:
    def __init__(
        self,
        hand: List[Card],
        current_color: str,
        top_value: str,
        card_counts: Dict[str, int] = None,
        hand_sizes: Dict[str, int] = None,
        my_player: str = "",
    ):
        self.hand = hand
        self.current_color = current_color
        self.top_value = top_value
        self.card_counts = card_counts or {}
        self.hand_sizes = hand_sizes or {}
        self.my_player = my_player


def _dfs(state: _SearchState, move: Move, depth: int) -> float:
    hand, color, value, counts = _apply_move_to_state(state, move)
    next_sizes = _update_hand_sizes(state.hand_sizes, state.my_player, move, len(hand))
    if not hand:
        return 1_000.0 - depth
    if depth == 1:
        return _heuristic(hand, color, next_sizes, counts, state.my_player)

    next_state = _SearchState(
        hand=hand,
        current_color=color,
        top_value=value,
        card_counts=counts,
        hand_sizes=next_sizes,
        my_player=state.my_player,
    )
    child_moves = _generate_moves(next_state)

    if not child_moves:
        return _heuristic(hand, color, next_sizes, counts, state.my_player)

    return max(_dfs(next_state, child, depth - 1) for child in child_moves)


def _generate_moves(state: _SearchState) -> List[Move]:
    moves: List[Move] = []
    for idx, card in enumerate(state.hand):
        if _can_play(card, state.current_color, state.top_value):
            move = {"type": "play", "card_index": idx, "card": card, "call_uno": len(state.hand) == 2}
            if card.get("type") == "wild":
                for color in ["red", "blue", "green", "yellow"]:
                    colored = dict(move)
                    colored["color_choice"] = color
                    moves.append(colored)
            else:
                moves.append(move)
    if not moves:
        moves.append({"type": "draw", "count": 1})
    return moves


def _apply_move_to_state(state: _SearchState, move: Move) -> Tuple[List[Card], str, str, Dict[str, int]]:
    hand = deepcopy(state.hand)
    color = state.current_color
    top_value = state.top_value
    counts = dict(state.card_counts)

    if move["type"] == "draw":
        hand.append({"color": None, "value": None, "type": "unknown"})
        return hand, color, top_value, counts

    idx = move.get("card_index")
    card = hand.pop(idx)
    top_value = card.get("value")
    if card.get("type") == "wild":
        color = move.get("color_choice") or _preferred_color(hand)
    else:
        color = card.get("color", color)

    if card.get("type") == "wild":
        key = f"wild_{card.get('value')}"
    else:
        key = f"{card.get('color')}_{card.get('value')}"
    if key in counts:
        counts[key] = max(0, counts[key] - 1)

    return hand, color, top_value, counts


def _heuristic(
    hand: List[Card],
    current_color: str,
    hand_sizes: Dict[str, int],
    card_counts: Dict[str, int],
    my_player: str,
) -> float:
    score = 220.0 - len(hand) * 22
    color_counts = Counter()
    action_by_color = Counter()
    wilds = 0

    for card in hand:
        color = card.get("color")
        value = card.get("value")
        if color:
            color_counts[color] += 1
            if color == current_color:
                score += 6
        if value in {"draw2", "skip", "reverse"}:
            action_by_color[color] += 1
            score += 12 if len(hand) <= 3 else 6
        if value == "wild_draw4":
            wilds += 1
            score += 25
        elif card.get("type") == "wild":
            wilds += 1
            score += 18

    if color_counts:
        strongest_color = max(color_counts.values())
        score += strongest_color * 5
        color_variety = sum(1 for cnt in color_counts.values() if cnt > 0)
        if color_variety > 2:
            score -= (color_variety - 2) * 4
        follow_up = color_counts.get(current_color, 0)
        score += follow_up * 4
        if follow_up == 0:
            score -= 10

    # Reward stacking action cards of same color
    for cnt in action_by_color.values():
        if cnt > 1:
            score += (cnt - 1) * 6

    score += wilds * 4  # general flexibility bonus

    # Prefer colors that are scarce in the remaining deck
    scarcity = _color_scarcity(card_counts)
    for color, cnt in color_counts.items():
        remaining = scarcity.get(color, 8)
        scarcity_bonus = max(0, 8 - remaining)
        score += cnt * scarcity_bonus * 0.8

    min_opp = min((size for player, size in hand_sizes.items() if player != my_player), default=99)
    if min_opp <= 2:
        score += 25 + wilds * 5

    if len(hand) <= 2:
        score += 18

    return score


def _can_play(card: Card, current_color: str, top_value: str) -> bool:
    if card.get("type") == "wild":
        return True
    if card.get("color") == current_color:
        return True
    return card.get("value") == top_value


def _preferred_color(hand: List[Card]) -> str:
    counts = {color: 0 for color in ["red", "blue", "green", "yellow"]}
    for card in hand:
        color = card.get("color")
        if color in counts:
            counts[color] += 1
    return max(counts.items(), key=lambda item: item[1])[0]


def _count_cards_in_play(hand: List[Card], discard_pile: List[Card]) -> Dict[str, int]:
    """Count how many of each card type remain available."""
    counts = {}
    colors = ["red", "blue", "green", "yellow"]
    number_values = [str(n) for n in range(10)]
    action_values = ["skip", "reverse", "draw2"]
    
    for color in colors:
        for value in number_values:
            counts[f"{color}_{value}"] = 2 if value != "0" else 1
        for value in action_values:
            counts[f"{color}_{value}"] = 2
    counts["wild_wild"] = 4
    counts["wild_wild_draw4"] = 4

    for card in hand + discard_pile:
        if card.get("type") == "wild":
            key = f"wild_{card.get('value')}"
            if key in counts:
                counts[key] = max(0, counts[key] - 1)
            continue
        color = card.get("color")
        value = card.get("value")
        if color in colors:
            key = f"{color}_{value}"
            if key in counts:
                counts[key] = max(0, counts[key] - 1)

    return counts


def _update_hand_sizes(hand_sizes: Dict[str, int], my_player: str, move: Move, my_new_size: int) -> Dict[str, int]:
    sizes = dict(hand_sizes) if hand_sizes else {}
    if my_player:
        sizes[my_player] = my_new_size
    card = move.get("card", {})
    value = card.get("value")
    if not sizes or move.get("type") != "play":
        return sizes

    opponents = [p for p in sizes.keys() if p != my_player]
    if not opponents:
        return sizes
    target = min(opponents, key=lambda p: sizes[p])
    if value == "draw2":
        sizes[target] = sizes.get(target, 0) + 2
    elif value == "wild_draw4":
        sizes[target] = sizes.get(target, 0) + 4
    elif value in ("skip", "reverse"):
        # Treat tempo gain as half-card advantage
        sizes[target] = max(0, sizes.get(target, 0) - 0.5)
    return sizes


def _color_scarcity(card_counts: Dict[str, int]) -> Dict[str, int]:
    totals = {color: 0 for color in ["red", "blue", "green", "yellow"]}
    for key, remaining in (card_counts or {}).items():
        if key.startswith("wild_"):
            continue
        if "_" not in key:
            continue
        color, _ = key.split("_", 1)
        if color in totals:
            totals[color] += remaining
    return totals

