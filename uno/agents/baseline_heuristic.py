import random
from typing import Dict
from collections import Counter
from uno.model import UnoGame

def baseline_heuristic(game: UnoGame) -> Dict:
    """
    A simple but solid UNO AI.

    Strategy (high level):
      1) Always play if you can.
      2) Prefer moves that reduce hand size and keep us in our strongest color.
      3) Use action cards (draw2/skip/reverse) aggressively when an opponent is close to winning.
      4) Save wild cards unless they help win soon or stop an opponent.
    """

    valid_moves = game.get_valid_moves()
    play_moves = [m for m in valid_moves if m.get('type') == 'play']
    if not play_moves:
        return {'type': 'draw', 'count': 1}

    my_hand = game.get_my_hand()
    hand_sizes = game.get_hand_sizes()
    current_color = game.get_current_color()

    colors = ['red', 'blue', 'green', 'yellow']
    color_counts = Counter(
        c.get('color') for c in my_hand if c.get('color') in colors
    )
    value_counts = Counter(
        c.get('value') for c in my_hand if c.get('value') is not None
    )

    opp_sizes = [s for p, s in hand_sizes.items() if p != game.my_player]
    min_opp = min(opp_sizes) if opp_sizes else 99
    has_non_wild_play = any(m['card'].get('type') != 'wild' for m in play_moves)

    def score(move: Dict) -> float:
        card = move.get('card', {})
        new_size = len(my_hand) - 1
        sc = 0.0

        # Winning is everything
        if new_size == 0:
            sc += 1000

        # Prefer getting rid of cards
        sc += 50 - new_size * 5

        value = card.get('value')
        ctype = card.get('type')
        ccolor = card.get('color')
        remaining_color_counts = color_counts.copy()
        if ccolor in remaining_color_counts:
            remaining_color_counts[ccolor] = max(0, remaining_color_counts[ccolor] - 1)

        # Action cards are strong, especially to block a low-hand opponent
        if value in ('draw2', 'skip', 'reverse', 'wild_draw4'):
            sc += 30
            if min_opp <= 2:
                sc += 70 if value in ('draw2', 'wild_draw4') else 50
            # Reward holding chains of action cards
            same_color_actions = sum(
                1 for c in my_hand
                if c.get('value') in ('draw2', 'skip', 'reverse')
                and c.get('color') == (move.get('color_choice') if ctype == 'wild' else ccolor)
            )
            if same_color_actions > 1:
                sc += same_color_actions * 6

        if ctype == 'wild':
            chosen = move.get('color_choice')
            # Choose a color we have many of
            sc += color_counts.get(chosen, 0) * 4

            # Use wilds more when an opponent is close to winning
            if min_opp <= 2:
                sc += 25

            # Discourage spending wild draw4 while we still have matching colors
            if value == 'wild_draw4' and has_non_wild_play and min_opp > 2:
                sc -= 30
            # Otherwise try to save wilds for later if we have alternatives
            if has_non_wild_play and len(my_hand) > 3 and min_opp > 2 and value != 'wild_draw4':
                sc -= 40
            # Bonus for landing on a color that leaves many follow-ups
            if chosen in colors:
                follow_up = remaining_color_counts.get(chosen, 0)
                sc += follow_up * 3
                if follow_up == 0:
                    sc -= 12
        else:
            # Prefer staying/landing on a color we hold a lot of
            sc += color_counts.get(ccolor, 0) * 2
            # Small bonus for keeping the current color (avoids giving control away)
            if ccolor == current_color:
                sc += 5
            else:
                # Penalize switching into a color we barely hold
                if color_counts.get(ccolor, 0) == 0:
                    sc -= 10
            follow_up = remaining_color_counts.get(ccolor, 0)
            sc += follow_up * 3
            if follow_up == 0:
                sc -= 8

        # Prefer dumping duplicate numbers early to diversify endgame options
        if value is not None:
            duplicates = max(0, value_counts.get(value, 0) - 1)
            sc += duplicates * 2

        # Avoid leaving a single inflexible action card as last card
        if new_size == 1 and ctype in ('wild',) and value != 'wild_draw4':
            sc -= 20

        return sc

    best = max(play_moves, key=score)
    best_score = score(best)
    best_moves = [m for m in play_moves if abs(score(m) - best_score) < 1e-9]
    return random.choice(best_moves)