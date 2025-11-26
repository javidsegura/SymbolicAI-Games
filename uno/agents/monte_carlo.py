import random
from copy import deepcopy
from typing import Any, Dict, List, Tuple

Card = Dict[str, Any]
Move = Dict[str, Any]


def monte_carlo_agent(game: Any, rollouts: int = 64, max_depth: int = 8) -> Move:
    """Estimate move quality via randomized rollouts with card counting."""

    valid_moves = game.get_valid_moves()
    if not valid_moves:
        return {"type": "draw", "count": 1}

    hand = game.get_my_hand()
    discard_pile = game.get_discard_pile()
    hand_sizes = game.get_hand_sizes()
    card_counts = _count_cards_in_play(hand, discard_pile)

    best_move = None
    best_score = float("-inf")

    for move in valid_moves:
        score = _estimate_move_value(
            move=move,
            hand=hand,
            top_card=game.get_top_card(),
            current_color=game.get_current_color(),
            rollouts=rollouts,
            max_depth=max_depth,
            card_counts=card_counts,
            hand_sizes=hand_sizes,
        )
        if score > best_score:
            best_score = score
            best_move = move

    return best_move or {"type": "draw", "count": 1}


def _estimate_move_value(
    move: Move,
    hand: List[Card],
    top_card: Card,
    current_color: str,
    rollouts: int,
    max_depth: int,
    card_counts: Dict[str, int],
    hand_sizes: Dict[str, int],
) -> float:
    score = 0.0
    for _ in range(rollouts):
        score += _rollout(move, hand, top_card, current_color, max_depth, card_counts, hand_sizes)
    return score / rollouts


def _rollout(
    move: Move,
    hand: List[Card],
    top_card: Card,
    current_color: str,
    max_depth: int,
    card_counts: Dict[str, int],
    hand_sizes: Dict[str, int],
) -> float:
    remaining, color, top_value = _apply_move(deepcopy(hand), move, top_card, current_color)
    if not remaining:
        return 1_000.0

    steps = 0
    draws = 0
    used_counts = dict(card_counts)

    while remaining and steps < max_depth:
        playable = [card for card in remaining if _can_play(card, color, top_value)]
        if playable:
            card = random.choice(playable)
            remaining.remove(card)
            top_value = card.get("value")
            color = card.get("color", color)
            if card.get("type") == "wild":
                color = random.choice(["red", "blue", "green", "yellow"])
        else:
            draws += 1
            drawn = _virtual_draw_informed(used_counts)
            remaining.append(drawn)
            _update_counts(used_counts, drawn)
        steps += 1

    min_opp = min(hand_sizes.values()) if hand_sizes else 99
    return 500.0 - len(remaining) * 25 - draws * 10 - steps * 5 - (min_opp * 2 if min_opp <= 2 else 0)


def _apply_move(hand: List[Card], move: Move, top_card: Card, current_color: str) -> Tuple[List[Card], str, str]:
    color = current_color
    top_value = top_card.get("value")

    if move["type"] == "draw":
        hand.append(_virtual_draw())
        return hand, color, top_value

    idx = move.get("card_index")
    if idx is None or not 0 <= idx < len(hand):
        return hand, color, top_value

    card = hand.pop(idx)
    top_value = card.get("value")
    if card.get("type") == "wild":
        color = move.get("color_choice") or _preferred_color(hand)
    else:
        color = card.get("color", color)

    return hand, color, top_value


def _preferred_color(hand: List[Card]) -> str:
    counts = {color: 0 for color in ["red", "blue", "green", "yellow"]}
    for card in hand:
        color = card.get("color")
        if color in counts:
            counts[color] += 1
    return max(counts.items(), key=lambda item: item[1])[0]


def _virtual_draw() -> Card:
    color = random.choice(["red", "blue", "green", "yellow"])
    value = random.choice(["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "skip", "reverse", "draw2"])
    ctype = "action" if value in {"skip", "reverse", "draw2"} else "normal"
    return {"color": color, "value": value, "type": ctype}


def _virtual_draw_informed(card_counts: Dict[str, int]) -> Card:
    """Draw a card weighted by what's likely still available."""
    colors = ["red", "blue", "green", "yellow"]
    values = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "skip", "reverse", "draw2"]
    
    color = random.choice(colors)
    value = random.choice(values)
    ctype = "action" if value in {"skip", "reverse", "draw2"} else "normal"
    
    key = f"{color}_{value}"
    if card_counts.get(key, 2) <= 0:
        color = random.choice(colors)
        value = random.choice(values)
        ctype = "action" if value in {"skip", "reverse", "draw2"} else "normal"
    
    return {"color": color, "value": value, "type": ctype}


def _update_counts(card_counts: Dict[str, int], card: Card) -> None:
    """Track that a card was drawn/used."""
    key = f"{card.get('color')}_{card.get('value')}"
    card_counts[key] = card_counts.get(key, 2) - 1


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


def _can_play(card: Card, current_color: str, top_value: str) -> bool:
    if card.get("type") == "wild":
        return True
    if card.get("color") == current_color:
        return True
    return card.get("value") == top_value

