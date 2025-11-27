import heapq
import random
from typing import Any, Dict, List, Tuple

Card = Dict[str, Any]
Move = Dict[str, Any]


def priority_queue_agent(game: Any) -> Move:
    """Greedy agent with card counting and hand tracking."""

    valid_moves = game.get_valid_moves()
    if not valid_moves:
        return {"type": "draw", "count": 1}

    hand = game.get_my_hand()
    hand_sizes = game.get_hand_sizes()
    discard_pile = game.get_discard_pile()
    current_color = game.get_current_color()
    card_counts = _count_cards_in_play(hand, discard_pile)
    
    pq: List[Tuple[float, float, Move]] = []

    for move in valid_moves:
        score = _score_move(move, hand, hand_sizes, current_color, card_counts)
        heapq.heappush(pq, (-score, random.random(), move))

    return heapq.heappop(pq)[2]


def _score_move(
    move: Move,
    hand: List[Card],
    hand_sizes: Dict[str, int],
    current_color: str,
    card_counts: Dict[str, int],
) -> float:
    if move["type"] == "draw":
        return -100.0

    card = move.get("card", {})
    score = 50.0 - len(hand) * 2

    if len(hand) == 2 and move.get("call_uno"):
        score += 40

    card_color = card.get("color")
    card_value = card.get("value")
    card_type = card.get("type")

    if card_type == "wild":
        score += 30
        if move.get("color_choice"):
            score += _color_density(hand, move["color_choice"]) * 5
    else:
        score += _color_density(hand, card_color) * 3
        if card_color == current_color:
            score += 10

    if card_value in {"draw2", "skip", "reverse"}:
        score += 25
        min_opp = min(hand_sizes.values(), default=99)
        if min_opp <= 2:
            score += 30

    if card_value in {"0", "1", "2"}:
        score += 5
    elif card_value in {"7", "8", "9"}:
        score -= 5

    key = f"{card_color}_{card_value}"
    remaining = card_counts.get(key, 0)
    if remaining == 0:
        score += 15
    elif remaining == 1:
        score += 5

    return score


def _color_density(hand: List[Card], color: str) -> int:
    return sum(1 for card in hand if card.get("color") == color)


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
    
    for card in hand + discard_pile:
        color = card.get("color")
        value = card.get("value")
        if color in colors:
            key = f"{color}_{value}"
            if key in counts:
                counts[key] = max(0, counts[key] - 1)
    
    return counts

