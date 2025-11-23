import json
import random
from typing import List, Optional, Tuple, Dict
from copy import deepcopy
import time

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
        best_move_overall = random.choice(moves) # Default random fallback
        time_limit = 8.5
        start_time = time.time()

        def simple_heuristic(move):
            r, c = move[1], move[2]
            # Check Winning Move (Fast check on coordinates first)
            if game.is_exit(r, c):
                return 2 
            # Check Capture
            if game.get_piece_at(r, c):
                return 1
            return 0

        # Move Ordering (speed-up for alpha-beta pruning) -- trying to get the best move first
        moves.sort(key=simple_heuristic, reverse=True)

        # Iterative depth-limited search
        for current_depth in range(1, self.max_depth + 1):
            # Check if we can time will allow for further exploration
            if time.time() - start_time > time_limit:
                print(f"   ⏳ Time limit reached. Stopping at Depth {current_depth-1}")
                break
            try:
                best_score_this_depth = float("-inf")
                best_move_this_depth = None

                alpha = float("-inf")
                beta = float("inf")

                for move in moves:
                    if time.time() - start_time > time_limit:
                        raise TimeoutError()

                    # Simulate the move
                    next_game = self._simulate_step(game, move)
                    
                    # Call recursive minimax (next turn is minimizing opponent)
                    score = self._minimax(next_game, 
                                        current_depth - 1, 
                                        is_maximizing=False,
                                        alpha=alpha,
                                        beta=beta)
                    
                    if score > best_score_this_depth:
                        best_score_this_depth = score
                        best_move_this_depth = move
                    
                    alpha = max(alpha, best_score_this_depth)
                best_move_overall = best_move_this_depth
                print(f"   ✅ Depth {current_depth} complete. Best: {best_score_this_depth}")
            except TimeoutError:
                print(f"   ⏳ Timed out during Depth {current_depth}")
                break

        return best_move_overall

    def _minimax(self, game: GhostsGame, depth: int, is_maximizing: bool, alpha: int, beta: int) -> float:
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
                eval_score = self._minimax(next_game, depth - 1, False, alpha, beta)
                max_eval = max(max_eval, eval_score)
                if eval_score >= beta:
                    break
                alpha = max(alpha, eval_score)
            return max_eval
        else:
            min_eval = float('inf')
            for move in moves:
                next_game = self._simulate_step(game, move)
                eval_score = self._minimax(next_game, depth - 1, True, alpha, beta)
                min_eval = min(min_eval, eval_score)
                if eval_score <= alpha:
                    break
                beta = min(beta, eval_score)
            return min_eval

    def _evaluate_state(self, game: GhostsGame) -> float:
        """
        Heuristic evaluation.
        Constraints: CANNOT inspect opponent ghost types (unless captured/revealed).
        """
        # 1. Material Status Evaluation
        material_score, is_terminal = self._evaluate_material_status(game)
        if is_terminal:
            return material_score
        
        score = material_score
        
        # 2. Opponent Risk/Reward Evaluation
        score += self._evaluate_opponent_risk_reward(game)
        
        # 3. Exit Distance Evaluation
        exit_score, is_win = self._evaluate_exit_distance(game)
        if is_win:
            return exit_score
        
        score += exit_score
        
        return score

    def _evaluate_material_status(self, game: GhostsGame) -> Tuple[float, bool]:
        """
        Evaluates material status based on my pieces.
        Returns: (score, is_terminal_state)
        """
        my_good = game.count_pieces(self.my_player, 'good')
        my_evil = game.count_pieces(self.my_player, 'evil')
        
        # Loss condition: I have no good ghosts left
        if my_good == 0:
            return (-10000.0, True)

        # Material Score: High value on keeping my Good ghosts
        score = (my_good * 100) + (my_evil * 20)  # Evil are less valuable, mainly for bluffing
        
        return (score, False)

    def _evaluate_opponent_risk_reward(self, game: GhostsGame) -> float:
        """
        Probabilistic reasoning about opponent pieces and risk/reward logic.
        """
        # Get active opponent pieces
        all_opp_pieces = game.get_opponent_pieces(include_captured=True)
        active_opponents = [p for p in all_opp_pieces if not p.get('captured')]

        # Calculate what's dead
        opp_revealed = game.get_revealed_pieces()
        dead_good = sum(1 for p in opp_revealed if p['type'] == 'good')
        dead_evil = sum(1 for p in opp_revealed if p['type'] == 'evil')
        
        remaining_good = 4 - dead_good
        remaining_evil = 4 - dead_evil
        total_unknown = len(active_opponents)
        
        # Probabilities
        if total_unknown > 0:
            prob_good = remaining_good / total_unknown
            prob_evil = remaining_evil / total_unknown
        else:
            prob_good = 0
            prob_evil = 0
        
        score = 0.0
        
        # SKEPTICISM CHECK: Are we at "Death's Door"? (Captured 3 Evil already)
        if dead_evil == 3:
            # PARANOID MODE.
            # We only capture if we are 100% sure it's GOOD.
            # If there is ANY uncertainty, we prefer the opponent piece to stay ALIVE.
            
            if prob_evil > 0:
                # We REWARD the existence of unknown pieces.
                # If we capture one, 'len(active_opponents)' goes down, score drops.
                # This forces the agent to avoid capturing.
                score += (len(active_opponents) * 50) 
            
            # Note: If prob_evil == 0 (We know for a fact it's good), 
            # we skip this and fall through to normal logic (optional, or handle explicitly)
        
        else:
            # NORMAL MODE
            # Calculate Expected Value of a capture
            ev_capture = (prob_good * 50) + (prob_evil * -50)
            
            if ev_capture > 0:
                # Likely Good: We want to capture.
                # We PENALIZE existence, so capturing removes penalty (improves score).
                score -= (len(active_opponents) * 20) 
                
                if prob_good > 0.75:
                    score -= (len(active_opponents) * 10) # Aggression bonus
            else:
                # Likely Evil: We want to avoid capturing.
                # We slightly REWARD existence (or penalize very little).
                # This tells agent: "It's okay if they stay."
                score += (len(active_opponents) * 10)
        
        return score

    def _evaluate_exit_distance(self, game: GhostsGame) -> Tuple[float, bool]:
        """
        Evaluates winning condition based on distance to exit.
        Returns: (score, is_win)
        """
        score = 0.0
        
        # Define exits
        exits = [(0, 0), (0, 5)] if self.my_player == '2' else [(5, 0), (5, 5)]
        
        my_pieces = game.get_my_pieces()
        for piece in my_pieces:
            if piece['type'] == 'good':
                r, c = piece['row'], piece['col']
                
                # Immediate Win Check
                if game.is_exit(r, c):
                    return (10000.0, True)
                
                # Distance calculation (Manhattan)
                # Max distance on 6x6 board is 10.
                dist = min(abs(r - er) + abs(c - ec) for er, ec in exits)
                
                # Add score: Closer is better.
                # Weighting this heavily to encourage movement.
                score += (15 - dist) * 5
        
        return (score, False)

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
        Randomized Setup Strategy.
        Randomly selects between a defensive, balanced, or tricky formation, 
        then shuffles the positions within that formation.
        """
        # Define rows: [Back Row, Front Row]
        # Player 1: Back=0, Front=1
        # Player 2: Back=5, Front=4
        rows = [0, 1] if self.my_player == '1' else [5, 4]
        cols = [1, 2, 3, 4]
        
        # Define Pools of pieces for [Back Row, Front Row]
        strategies = [
            # 1. THE PHALANX (Classic)
            # Back: 4 Good | Front: 4 Evil
            # Good for beginners, keeps Good ghosts safe.
            (['good']*4, ['evil']*4),
            
            # 2. THE AMBUSH (Mixed)
            # Back: 3 Good, 1 Evil | Front: 3 Evil, 1 Good
            # Puts one Good ghost in front to rush out, and one Evil in back to catch deep invaders.
            (['good', 'good', 'good', 'evil'], ['evil', 'evil', 'evil', 'good']),
            
            # 3. THE CHAOS (Balanced)
            # Back: 2 Good, 2 Evil | Front: 2 Good, 2 Evil
            # Maximum confusion. Hardest for opponent to read.
            (['good', 'good', 'evil', 'evil'], ['good', 'good', 'evil', 'evil'])
        ]
        
        # 1. Pick a strategy randomly
        back_pool, front_pool = random.choice(strategies)
        
        # 2. Shuffle the specific column assignments
        # This ensures that even if we pick "The Phalanx", the opponent 
        # doesn't know WHICH Evil ghost is where (though in Phalanx they are all evil).
        # For "The Chaos", this is crucial.
        random.shuffle(back_pool)
        random.shuffle(front_pool)
        
        setup = []
        
        # 3. Assign to board
        # Place Back Row
        for i, col in enumerate(cols):
            setup.append({'row': rows[0], 'col': col, 'type': back_pool[i]})
            
        # Place Front Row
        for i, col in enumerate(cols):
            setup.append({'row': rows[1], 'col': col, 'type': front_pool[i]})
            
        return setup

# ==========================================
# EXECUTION
# ==========================================

# Create the agent instance
agent = SimpleMinimaxAgent(max_depth=10)

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
    stats, all_results = result
    print(f"Results: {stats}")
    print(f"Game times (seconds): {stats['game_times']}")
    print(f"Average game time: {sum(stats['game_times']) / len(stats['game_times']) if stats['game_times'] else 0:.2f} seconds")