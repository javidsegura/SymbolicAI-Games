import json
import random
from typing import List, Optional, Tuple, Dict
from copy import deepcopy

# Assuming your utils are in the path or same file
from ghosts.debugging.utils import GhostsGame, play_game, BASE_URL

class SimpleMinimaxAgent:
    """
    An OOP Minimax agent without Alpha-Beta pruning.
    It respects hidden information (does not peek at opponent types).
    """

    def __init__(self, max_depth: int = 2):
        self.max_depth = max_depth
        self.my_player = None

    def choose_move(self, game: GhostsGame) -> Optional[List[int]]:
        """
        Public API: Called by the game loop to get the next action.
        """
        self.my_player = game.my_player

        # 1. Handle Setup Phase
        if game.is_setup_phase():
            if not game.setup_complete():
                return self._get_setup_strategy()
            return None

        # 2. Handle Playing Phase
        print(f"🤖 Agent Thinking (Depth {self.max_depth})...")
        
        # Get valid moves
        moves = game.get_valid_moves()
        if not moves:
            return None

        # Run Minimax to find the best move
        # We start as Maximizing player
        best_score = float('-inf')
        best_move = random.choice(moves) # Default random fallback

        for move in moves:
            # Simulate the move
            next_game = self._simulate_step(game, move)
            
            # Call recursive minimax (next turn is minimizing opponent)
            score = self._minimax(next_game, self.max_depth - 1, is_maximizing=False)
            
            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    def _minimax(self, game: GhostsGame, depth: int, is_maximizing: bool) -> float:
        """
        Recursive Minimax function (No Pruning).
        """
        # Base Case: Leaf node or Terminal State
        if depth == 0 or game.is_terminal():
            return self._evaluate_state(game)

        moves = game.get_valid_moves()
        if not moves:
            return self._evaluate_state(game)

        if is_maximizing:
            max_eval = float('-inf')
            for move in moves:
                next_game = self._simulate_step(game, move)
                eval_score = self._minimax(next_game, depth - 1, False)
                max_eval = max(max_eval, eval_score)
            return max_eval
        else:
            min_eval = float('inf')
            for move in moves:
                next_game = self._simulate_step(game, move)
                eval_score = self._minimax(next_game, depth - 1, True)
                min_eval = min(min_eval, eval_score)
            return min_eval

    def _evaluate_state(self, game: GhostsGame) -> float:
        """
        Heuristic evaluation.
        Constraints: CANNOT inspect opponent ghost types (unless captured/revealed).
        """
        score = 0.0
        
        # 1. MY STATUS (I know everything about my pieces)
        my_good = game.count_pieces(self.my_player, 'good')
        my_evil = game.count_pieces(self.my_player, 'evil')
        
        # Loss condition: I have no good ghosts left
        if my_good == 0:
            return -10000.0

        # Material Score: High value on keeping my Good ghosts
        score += (my_good * 100)
        score += (my_evil * 20)  # Evil are less valuable, mainly for bluffing

        # 2. PROBABILISTIC REASONING ON A PIECE 

        # 3. WINNING CONDITION (Distance to Exit)
        # This is the most "reliable" heuristic without knowing opponent types.
        # Push my Good ghosts toward the exits.
        
        # Define exits
        exits = [(0, 0), (0, 5)] if self.my_player == '2' else [(5, 0), (5, 5)]
        
        my_pieces = game.get_my_pieces()
        for piece in my_pieces:
            if piece['type'] == 'good':
                r, c = piece['row'], piece['col']
                
                # Immediate Win Check
                if game.is_exit(r, c):
                    return 10000.0
                
                # Distance calculation (Manhattan)
                # Max distance on 6x6 board is 10.
                dist = min(abs(r - er) + abs(c - ec) for er, ec in exits)
                
                # Add score: Closer is better.
                # Weighting this heavily to encourage movement.
                score += (15 - dist) * 5

        return score

    def _simulate_step(self, game: GhostsGame, move: List[int]) -> GhostsGame:
        """
        Helper to simulate a move and return a NEW GhostsGame object.
        """
        # simulate_move returns a dictionary representing the new state
        new_state_dict = game.simulate_move(move)
        
        # Determine who plays next
        current_player = game.current_player
        next_player = game.get_opponent(current_player)
        
        # Reconstruct game object
        return GhostsGame(
            json.dumps(new_state_dict), 
            'playing', 
            next_player, 
            self.my_player
        )

    def _get_setup_strategy(self) -> List[Dict]:
        """
        Defines the initial board setup.
        Strategy: Good in back (safety), Evil in front (bluff/protection).
        """
        if self.my_player == '1':
            return [
                {'row': 1, 'col': 1, 'type': 'evil'}, {'row': 1, 'col': 2, 'type': 'evil'},
                {'row': 1, 'col': 3, 'type': 'evil'}, {'row': 1, 'col': 4, 'type': 'evil'},
                {'row': 0, 'col': 1, 'type': 'good'}, {'row': 0, 'col': 2, 'type': 'good'},
                {'row': 0, 'col': 3, 'type': 'good'}, {'row': 0, 'col': 4, 'type': 'good'}
            ]
        else:
            return [
                {'row': 4, 'col': 1, 'type': 'evil'}, {'row': 4, 'col': 2, 'type': 'evil'},
                {'row': 4, 'col': 3, 'type': 'evil'}, {'row': 4, 'col': 4, 'type': 'evil'},
                {'row': 5, 'col': 1, 'type': 'good'}, {'row': 5, 'col': 2, 'type': 'good'},
                {'row': 5, 'col': 3, 'type': 'good'}, {'row': 5, 'col': 4, 'type': 'good'}
            ]

# ==========================================
# EXECUTION
# ==========================================

# Create the agent instance
agent = SimpleMinimaxAgent(max_depth=2)

def my_agent_wrapper(game: GhostsGame): # DEBUG: review if this is fine
    """ 
    Wrapper function required by the play_game utility.
    """
    return agent.choose_move(game)

if __name__ == "__main__":
    STUDENT_TOKEN = 'JAVIER_DOMINGUEZ'  
    SOLVER = my_agent_wrapper
    
    result = play_game(
        solver=SOLVER,
        base_url=BASE_URL,
        token=STUDENT_TOKEN,
        game_type='ghosts',
        game_class=GhostsGame,
        num_games=10,
        debug=False,
        verbose=True
    )