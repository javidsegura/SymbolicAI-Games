import json
from typing import Dict, List


class UnoGame:
    """Represents UNO game state."""

    def __init__(self, state: str, status: str, current_player: str, my_player: str):
        self.state_str = state
        self.status = status
        self.current_player = current_player
        self.my_player = my_player
        self._state = None
        print("✅ UnoGame class loaded")

    @property
    def state(self) -> Dict:
        if self._state is None:
            self._state = json.loads(self.state_str)
        return self._state

    def get_my_hand(self) -> List[Dict]:
        return self.state['hands'].get(self.my_player, [])

    def get_hand_sizes(self) -> Dict[str, int]:
        hands = self.state.get('hands', {})
        return {player: len(hand) for player, hand in hands.items()}

    def get_current_color(self) -> str:
        return self.state.get('current_color', '')

    def get_top_card(self) -> Dict:
        discard_pile = self.state.get('discard_pile', [])
        return discard_pile[-1] if discard_pile else {}

    def get_discard_pile(self) -> List[Dict]:
        """Get the full discard pile (all cards that have been played)."""
        return self.state.get('discard_pile', [])

    def get_discard_pile_size(self) -> int:
        """Get the number of cards in the discard pile."""
        return len(self.state.get('discard_pile', []))

    def is_terminal(self) -> bool:
        return self.status == 'complete'

    def _can_play_card(self, card: Dict, top_card: Dict, current_color: str) -> bool:
        if not top_card:
            return True
        if card.get('type') == 'wild':
            return True
        if card.get('color') == current_color:
            return True
        if card.get('value') == top_card.get('value'):
            return True
        return False

    def get_valid_moves(self) -> List[Dict]:
        if self.current_player != self.my_player:
            return []
        
        hand = self.get_my_hand()
        top_card = self.get_top_card()
        current_color = self.get_current_color()
        valid_moves = []
        
        for i, card in enumerate(hand):
            if self._can_play_card(card, top_card, current_color):
                move = {'type': 'play', 'card_index': i, 'card': card, 'call_uno': len(hand) == 2}
                if card.get('type') == 'wild':
                    for color in ['red', 'blue', 'green', 'yellow']:
                        color_move = move.copy()
                        color_move['color_choice'] = color
                        valid_moves.append(color_move)
                else:
                    valid_moves.append(move)
        
        valid_moves.append({'type': 'draw', 'count': 1})
        return valid_moves

    def print_state(self):
        print(f"\n{'='*50}")
        print(f"Current Turn: Player {self.current_player}")
        print(f"Current Color: {self.get_current_color().upper()}")
        top_card = self.get_top_card()
        if top_card:
            print(f"Top Card: {top_card.get('color')} {top_card.get('value')}")
        hand_sizes = self.get_hand_sizes()
        print("\nHand Sizes:")
        for p in sorted(hand_sizes.keys()):
            if p != self.my_player:
                print(f"  Player {p}: {hand_sizes[p]} cards")
        my_hand = self.get_my_hand()
        print(f"\nYour Hand ({len(my_hand)} cards):")
        for i, card in enumerate(my_hand):
            print(f"  {i}: {card.get('color')} {card.get('value')}")
        print('='*50)