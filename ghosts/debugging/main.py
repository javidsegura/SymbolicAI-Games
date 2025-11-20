import requests
import json
import time
import random
from typing import List, Optional, Tuple, Any, Dict
from copy import deepcopy

from ghosts.debugging.utils import get_default_setup, GhostsGame


def my_agent(game: GhostsGame) -> List:
    """
    Your AI implementation.
    
    Args:
        game: GhostsGame object with helper methods
    
    Returns:
        Setup (list of 8 pieces) or Move (list of [piece_id, row, col])
    """
    
    # ============================================================
    # SETUP PHASE
    # ============================================================
    if game.is_setup_phase() and not game.setup_complete():
        # TODO: Implement your setup strategy!
        # For now, use default setup
        return get_default_setup(game.my_player)
        
        # Example: Custom setup (remember: columns must be 1-4)
        # if game.my_player == '1':
        #     return create_custom_setup('1',
        #                               [(0, 1), (0, 2), (1, 1), (1, 2)],  # good ghosts
        #                               [(0, 3), (0, 4), (1, 3), (1, 4)])  # evil ghosts
    
    # ============================================================
    # PLAYING PHASE
    # ============================================================
    
    # Get basic info
    my_pieces = game.get_my_pieces()
    opponent_pieces = game.get_opponent_pieces()
    
    # ============================================================
    # TODO: IMPLEMENT YOUR ALGORITHM HERE!
    # ============================================================
    
    # Example: Random valid move (replace with your algorithm!)
    moves = game.get_valid_moves()
    
    if not moves:
        return None
    
    # Just pick a random move
    return random.choice(moves)
    
    # ============================================================
    # Ideas to try:
    # 1. Consider not using the same setup strategy all the time
    # 2. Advance good ghosts toward exits (row 5 for P1, row 0 for P2)
    # 3. ... but try not to expose them to easy captures or reveal them
    # 4. Use evil ghosts as blockers or to safely capture
    # 5. Implement expectiminimax for handling hidden information
    # 6. Use probabilistic reasoning about unrevealed ghosts
    # ============================================================

print("✅ Solver function defined")
print("   Remember to implement your algorithm before running!")

if __name__ == "__main__":
      # Create a test state
      test_state = {
      'pieces': {
            '1': [
                  {'id': 0, 'row': 2, 'col': 1, 'type': 'good', 'captured': False},
                  {'id': 1, 'row': 2, 'col': 3, 'type': 'good', 'captured': False},
                  {'id': 2, 'row': 1, 'col': 1, 'type': 'good', 'captured': False},
                  {'id': 3, 'row': 1, 'col': 3, 'type': 'good', 'captured': False},
                  {'id': 4, 'row': 1, 'col': 2, 'type': 'evil', 'captured': False},
                  {'id': 5, 'row': 1, 'col': 4, 'type': 'evil', 'captured': False},
                  {'id': 6, 'row': 2, 'col': 2, 'type': 'evil', 'captured': False},
                  {'id': 7, 'row': 2, 'col': 4, 'type': 'evil', 'captured': False},
            ],
            '2': [
                  {'id': 0, 'row': 3, 'col': 1, 'type': 'good', 'captured': False},
                  {'id': 1, 'row': 3, 'col': 4, 'type': 'good', 'captured': False},
                  {'id': 2, 'row': 4, 'col': 1, 'type': 'good', 'captured': False},
                  {'id': 3, 'row': 4, 'col': 4, 'type': 'good', 'captured': False},
                  {'id': 4, 'row': 4, 'col': 2, 'type': 'evil', 'captured': False},
                  {'id': 5, 'row': 4, 'col': 3, 'type': 'evil', 'captured': False},
                  {'id': 6, 'row': 3, 'col': 2, 'type': 'evil', 'captured': False},
                  {'id': 7, 'row': 3, 'col': 3, 'type': 'evil', 'captured': False},
            ]
      },
      'revealed': {'1': [], '2': []}
      }

      test_game = GhostsGame(json.dumps(test_state), 'playing', '1', '1')

      print("Test board:")
      test_game.print_board()

      print(f"\nValid moves: {test_game.get_valid_moves()}")

      # Test your solver
      move = my_agent(test_game)
      print(f"\nYour solver chose: {move}")

      # STUDENT_TOKEN = 'JAVER-DOMINGUEZ'  # e.g., 'JOHN-DOE'
      # SOLVER = my_agent  # Change to manual_player_solver to play manually
      # MULTIPLAYER = False
      # MATCH_ID = None
      # NUM_GAMES = 1

      # result = play_game(
      #       solver=SOLVER,
      #       base_url=BASE_URL,
      #       token=STUDENT_TOKEN,
      #       game_type='ghosts',
      #       game_class=GhostsGame,
      #       multiplayer=MULTIPLAYER,
      #       match_id=MATCH_ID,
      #       num_games=NUM_GAMES,
      #       debug=False,
      #       verbose=True
      # )

      # stats, all_results = result
      # print("\n📊 Summary:")
      # print(f"   Record: {stats['wins']}W - {stats['losses']}L - {stats['draws']}D")
      # print(f"   Win Rate: {stats['win_rate']*100:.1f}%")