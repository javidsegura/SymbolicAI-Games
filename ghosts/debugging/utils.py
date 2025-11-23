import requests
import json
import time
import random
from typing import List, Optional, Tuple, Any, Dict
from copy import deepcopy

print("✅ Dependencies imported")

BASE_URL = 'https://ie-aireasoning-gr4r5bl6tq-ew.a.run.app'  # Your Cloud Run URL

print("✅ Configuration loaded")

class GameClient:
    def __init__(self, base_url: str, token: str, debug: bool = False):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.debug = debug

    def _make_request(self, endpoint: str, params: dict, max_retries: int = 10) -> dict:
        params['TOKEN'] = self.token
        url = f'{self.base_url}{endpoint}'

        for attempt in range(max_retries):
            try:
                if self.debug:
                    print(f"[DEBUG] Request: {endpoint}")
                    print(f"[DEBUG] Params: {params}")

                response = requests.get(url, params=params, timeout=30)

                if self.debug:
                    print(f"[DEBUG] Response [{response.status_code}]: {response.text[:200]}")

                if response.status_code == 200:
                    if response.text:
                        try:
                            return response.json()
                        except (json.JSONDecodeError, ValueError) as e:
                            if self.debug:
                                print(f"[DEBUG] Non-JSON response: {response.text[:100]}")
                            return {}
                    return {}
                else:
                    print(f"⚠️  HTTP {response.status_code}: {response.text[:200]}")

            except requests.exceptions.Timeout:
                print(f"⚠️  Request timeout (attempt {attempt + 1}/{max_retries})")
            except requests.exceptions.RequestException as e:
                print(f"⚠️  Request error: {e} (attempt {attempt + 1}/{max_retries})")
            except Exception as e:
                print(f"⚠️  Unexpected error: {type(e).__name__}: {e} (attempt {attempt + 1}/{max_retries})")

            if attempt < max_retries - 1:
                time.sleep(1)

        raise Exception(f"Failed to connect to {endpoint} after {max_retries} attempts")

    def create_match(self, game_type: str, num_games: int, multiplayer: bool = False) -> str:
        response = self._make_request('/new-match', {
            'game-type': game_type,
            'num-games': str(num_games),
            'multi-player': 'True' if multiplayer else 'False'
        })
        
        if 'match-id' not in response:
            print(f"❌ Server response missing 'match-id'. Response: {response}")
            raise KeyError(f"Server response missing 'match-id'. Got: {response}")
        
        return response['match-id']

    def join_match(self, match_id: str) -> dict:
        response = self._make_request('/join-match', {
            'match-id': match_id
        })
        return response

    def get_game_state(self, match_id: str, game_index: int) -> dict:
        return self._make_request('/game-state-in-match', {
            'match-id': match_id,
            'game-index': str(game_index)
        })

    def get_match_state(self, match_id: str) -> dict:
        return self._make_request('/match-state', {
            'match-id': match_id
        })

    def make_move(self, match_id: str, player: str, move: Any) -> bool:
        move_str = move if isinstance(move, str) else json.dumps(move)
        
        self._make_request('/make-move-in-match', {
            'match-id': match_id,
            'player': player,
            'move': move_str
        })
        return True

print("✅ GameClient loaded")


def play_game(
    solver,
    base_url: str,
    token: str,
    game_type: str,
    game_class,
    multiplayer: bool = False,
    match_id: Optional[str] = None,
    num_games: int = 1,
    debug: bool = False,
    verbose: bool = True
) -> Tuple:
    client = GameClient(base_url, token, debug=debug)

    if match_id is None:
        if verbose:
            print(f"🎮 Creating new match: {num_games} x {game_type}")
        match_id = client.create_match(game_type, num_games, multiplayer)
        if verbose:
            print(f"   Match ID: {match_id}")

    if verbose:
        print(f"🔗 Joining match {match_id}...")
    match = client.join_match(match_id)
    player = match['player']
    num_games = match.get('num-games', num_games)
    if verbose:
        print(f"   You are player: {player}")

    game_state = client.get_game_state(match_id, 0)
    if game_state['status'] == 'waiting':
        if verbose:
            print("⏳ Waiting for opponent to join...")
        while game_state['status'] == 'waiting':
            time.sleep(2)
            game_state = client.get_game_state(match_id, 0)

    all_results = []
    wins = 0
    losses = 0
    draws = 0
    game_times = []

    while True:
        match_state = client.get_match_state(match_id)
        if match_state['status'] != 'in_progress':
            break
        game_num = match_state['current-game-index']

        if verbose:
            print(f"\n{'='*50}")
            print(f"🎮 GAME {game_num + 1}/{num_games}")
            print(f"{'='*50}\n")

        # Start timing for this game
        game_start_time = time.time()

        # Get initial game state and check player assignment
        game_state = client.get_game_state(match_id, game_num)
        
        # Update player sign if it changed (randomized per game)
        if 'my-player' in game_state and game_state['my-player']:
            new_player = game_state['my-player']
            if new_player != player and verbose and game_num > 0:
                print(f"ℹ️  Player assignment changed: You are now Player {new_player}\n")
            player = new_player
        
        game = game_class(game_state['state'], game_state['status'], game_state['player'], player)

        move_count = 0
        # Handle setup phase
        while game_state['status'] == 'setup':
            game_state = client.get_game_state(match_id, game_num)
            player = game_state.get('my-player', player)
            if 'winner' in game_state or game_state['status'] != 'setup':
                break

            game = game_class(game_state['state'], game_state['status'], game_state['player'], player)
            
            # Check if this player needs to complete setup
            if game.is_setup_phase() and not game.setup_complete():
                if verbose:
                    print(f"\n🎯 SETUP PHASE - Player {player}")
                    print(f"   Submitting your ghost setup...")

                try:
                    setup = solver(game)
                    
                    if verbose:
                        print(f"   ✅ Setup submitted!")

                    client.make_move(match_id, player, setup)

                except Exception as e:
                    print(f"❌ Error in solver during setup: {e}")
                    import traceback
                    traceback.print_exc()
                    all_results.append(('error', None))
                    break
            else:
                if verbose:
                    print(f"⏳ Waiting for opponent to complete setup...")
                time.sleep(2)

        # Now in playing phase - continue until complete
        while game_state['status'] == 'playing':
            game_state = client.get_game_state(match_id, game_num)
            player = game_state.get('my-player', player)
            if 'winner' in game_state or game_state['status'] == 'complete':
                break

            game = game_class(game_state['state'], game_state['status'], game_state['player'], player)
            
            if game.is_terminal():
                break

            if verbose:
                game.print_board()

            if game.current_player == player:
                if verbose:
                    print(f"🤔 Your turn (Player {player})...")

                try:
                    move = solver(game)

                    if verbose and move and isinstance(move, list) and len(move) == 3:
                        print(f"   Moving ghost {move[0]} to ({move[1]}, {move[2]})")

                    client.make_move(match_id, player, move)
                    move_count += 1

                except Exception as e:
                    print(f"❌ Error in solver: {e}")
                    import traceback
                    traceback.print_exc()
                    all_results.append(('error', None))
                    break
            else:
                if verbose:
                    print(f"⏳ Waiting for opponent (Player {game.current_player})...")
                time.sleep(2)

        # game is complete
        game_state = client.get_game_state(match_id, game_num)
        game = game_class(game_state['state'], game_state['status'], game_state['player'], player)
        
        # Calculate game duration
        game_duration = time.time() - game_start_time
        game_times.append(game_duration)
        
        if verbose:
            game.print_board()
            print("=" * 40)
            print(f"⏱️  Game duration: {game_duration:.2f} seconds")

        winner = game_state.get('winner', '-')
        if winner == '-':
            if verbose:
                print("🤝 Game ended in a DRAW!")
            result = 'draw'
            draws += 1
        elif winner == player:
            if verbose:
                print("🎉 You WON! Congratulations!")
            result = 'win'
            wins += 1
        else:
            if verbose:
                print("😞 You LOST. Better luck next time!")
            result = 'loss'
            losses += 1

        all_results.append((result, player, winner))

        if verbose and num_games > 1:
            print(f"\n📊 Current Record: {wins}W - {losses}L - {draws}D")
            print(f"   Games Remaining: {num_games - game_num - 1}\n")

    # Return results
    stats = {
        'wins': wins,
        'losses': losses,
        'draws': draws,
        'total_games': num_games,
        'win_rate': wins / num_games if num_games > 0 else 0,
        'player': player,
        'match_id': match_id,
        'game_times': game_times
    }

    return stats, all_results

print("✅ play_game loaded")

class GhostsGame:
    """
    Represents Ghosts game state with helper methods.
    
    Key methods for your solver:
    - game.get_my_pieces()             # Your pieces (with hidden types)
    - game.get_opponent_pieces()       # Opponent pieces (types hidden unless captured)
    - game.get_revealed_pieces()       # Opponent pieces you've captured (types revealed)
    - game.get_valid_moves()           # All valid moves for your pieces
    - game.is_exit(row, col)           # Check if position is a winning exit
    - game.simulate_move(move)         # Simulate move for search
    - game.is_terminal()               # Check if game over
    - game.is_setup_phase()            # Check if in setup phase
    - game.print_board()               # Debug visualization
    """

    def __init__(self, state: str, status: str, current_player: str, my_player: str):
        self.state_str = state
        self.status = status
        self.current_player = current_player
        self.my_player = my_player
        self._state = None
        self._valid_moves = None

    @property
    def state(self) -> Dict:
        """Get state dictionary."""
        if self._state is None:
            self._state = json.loads(self.state_str)
        return self._state

    def is_setup_phase(self) -> bool:
        """Check if game is in setup phase."""
        return self.status == 'setup' or self.state.get('phase') == 'setup'

    def setup_complete(self) -> bool:
        """Check if this player has completed setup."""
        if not self.is_setup_phase():
            return True
        return self.state.get('setup_complete', {}).get(self.my_player, False)

    def get_my_pieces(self) -> List[Dict]:
        """Get your pieces (you know their types)."""
        if self.my_player not in self.state.get('pieces', {}):
            return []
        return [p for p in self.state['pieces'][self.my_player] if not p.get('captured', False)]

    def get_opponent_pieces(self, include_captured: bool = False) -> List[Dict]:
        """Get opponent pieces (types hidden unless revealed by capture)."""
        opponent = '2' if self.my_player == '1' else '1'
        if opponent not in self.state.get('pieces', {}):
            return []
        pieces = self.state['pieces'][opponent]
        
        if include_captured:
            return pieces
        else:
            return [p for p in pieces if not p.get('captured', False)]

    def get_revealed_pieces(self) -> List[Dict]:
        """Get opponent pieces whose types have been revealed to you."""
        opponent = '2' if self.my_player == '1' else '1'
        revealed_ids = self.state.get('revealed', {}).get(opponent, [])
        
        revealed_pieces = []
        for piece in self.state.get('pieces', {}).get(opponent, []):
            if piece.get('id') in revealed_ids:
                revealed_pieces.append(piece)
        return revealed_pieces

    def is_terminal(self) -> bool:
        """Check if game is over."""
        return self.status == 'complete'

    def is_waiting(self) -> bool:
        """Check if waiting for opponent."""
        return self.status == 'waiting'

    def get_opponent(self, player: str) -> str:
        """Get opponent's identifier."""
        return '2' if player == '1' else '1'

    def is_exit(self, row: int, col: int) -> bool:
        """Check if position is a winning exit for your good ghosts."""
        # Player 1 wins at bottom exits (row 5, cols 0 and 5)
        # Player 2 wins at top exits (row 0, cols 0 and 5)
        if self.my_player == '1':
            return row == 5 and col in [0, 5]
        else:
            return row == 0 and col in [0, 5]

    def get_piece_at(self, row: int, col: int) -> Optional[Tuple[str, Dict]]:
        """Get piece at position. Returns (player, piece) or None."""
        for player in ['1', '2']:
            if player not in self.state.get('pieces', {}):
                continue
            for piece in self.state['pieces'][player]:
                if not piece.get('captured', False) and piece.get('row') == row and piece.get('col') == col:
                    return player, piece
        return None

    def get_valid_moves(self, player: Optional[str] = None) -> List[List[int]]:
        """Get all valid moves for player. Returns list of [piece_id, row, col]."""
        if player is None:
            player = self.my_player

        # No moves during setup
        if self.is_setup_phase():
            return []

        if self._valid_moves is None or player != self.current_player:
            moves = []
            for piece in self.state.get('pieces', {}).get(player, []):
                if piece.get('captured', False):
                    continue

                row, col = piece.get('row'), piece.get('col')
                piece_id = piece.get('id')

                # Try all four directions
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    new_row = row + dr
                    new_col = col + dc

                    # Check bounds
                    if 0 <= new_row < 6 and 0 <= new_col < 6:
                        # Check if square is occupied
                        occupant = self.get_piece_at(new_row, new_col)

                        # Exits at corners - can only move there if it's a winning move
                        is_corner = (new_row == 0 or new_row == 5) and (new_col == 0 or new_col == 5)
                        if is_corner:
                            # Only allow if it's a winning exit for a good ghost
                            if piece.get('type') == 'good' and self.is_exit(new_row, new_col):
                                moves.append([piece_id, new_row, new_col])
                            # Otherwise, corners are blocked (can't stop there)
                        else:
                            # Regular square: can move to empty square or capture opponent
                            if occupant is None or occupant[0] != player:
                                moves.append([piece_id, new_row, new_col])

            self._valid_moves = moves
        return self._valid_moves

    def simulate_move(self, move: List[int]) -> Dict:
        """
        Simulate a move and return new state.
        Does NOT contact server or modify original state.
        """
        new_state = deepcopy(self.state)
        player = self.current_player
        opponent = self.get_opponent(player)

        piece_id, new_row, new_col = move[0], move[1], move[2]

        # Find and move the piece
        for piece in new_state['pieces'][player]:
            if piece['id'] == piece_id:
                # Check if capturing
                for opp_piece in new_state['pieces'][opponent]:
                    if not opp_piece['captured'] and opp_piece['row'] == new_row and opp_piece['col'] == new_col:
                        opp_piece['captured'] = True
                        # Reveal BOTH pieces: captured piece AND capturing piece
                        if opp_piece['id'] not in new_state['revealed'][opponent]:
                            new_state['revealed'][opponent].append(opp_piece['id'])
                        if piece_id not in new_state['revealed'][player]:
                            new_state['revealed'][player].append(piece_id)
                        break

                # Move piece
                piece['row'] = new_row
                piece['col'] = new_col
                break

        return new_state

    def count_pieces(self, player: str, piece_type: str, state: Optional[Dict] = None) -> int:
        """Count remaining pieces of a type for a player."""
        if state is None:
            state = self.state

        count = 0
        for piece in state.get('pieces', {}).get(player, []):
            if not piece.get('captured', False) and piece.get('type') == piece_type:
                count += 1
        return count

    def print_board(self):
        """Print board visualization (works for both setup and playing phases)."""
        state = self.state
        opponent = self.get_opponent(self.my_player)

        # Header
        print("\n" + "=" * 50)
        if self.is_setup_phase():
            print(f"SETUP PHASE - Player {self.my_player}")
            print(f"Setup complete: {self.setup_complete()}")
        else:
            print(f"Player {self.my_player} (You) - Good: {self.count_pieces(self.my_player, 'good')}, Evil: {self.count_pieces(self.my_player, 'evil')}")
            print(f"Player {opponent} (Opp) - Good: {self.count_pieces(opponent, 'good')}, Evil: {self.count_pieces(opponent, 'evil')}")
        print("=" * 50)
        
        # Column headers
        print("  0   1   2   3   4   5")
        print("┌" + "───┬" * 5 + "───┐")

        # Board rows
        for r in range(6):
            row_str = ""
            for c in range(6):
                cell = "   "
                
                # Check for pieces from both players
                for player in ['1', '2']:
                    if player not in state.get('pieces', {}):
                        continue
                    for piece in state['pieces'][player]:
                        if not piece.get('captured', False) and piece.get('row') == r and piece.get('col') == c:
                            if player == self.my_player:
                                # Show your pieces with type
                                symbol = 'G' if piece.get('type') == 'good' else 'E'
                                cell = f" {symbol} "
                            else:
                                # Show opponent pieces (unknown unless revealed)
                                if piece.get('id') in state.get('revealed', {}).get(player, []):
                                    symbol = 'g' if piece.get('type') == 'good' else 'e'
                                    cell = f" {symbol} "
                                else:
                                    cell = " ? "
                            break
                
                # Mark exits at corners
                if (r == 0 or r == 5) and (c == 0 or c == 5):
                    if cell == "   ":
                        cell = " X "

                row_str += "│" + cell
            row_str += "│ " + str(r)
            print(row_str)
            
            if r < 5:
                print("├" + "───┼" * 5 + "───┤")

        print("└" + "───┴" * 5 + "───┘")
        
        # Legend
        if self.is_setup_phase():
            print("\nLegend: G=good ghost, E=evil ghost, X=exit")
            if self.my_player == '1':
                print("Your setup area: Rows 0-1, Columns 1-4")
            else:
                print("Your setup area: Rows 4-5, Columns 1-4")
            print("Note: Exits (X) can only be entered by good ghosts to win!")
        else:
            print("\nLegend: G=your good, E=your evil, ?=unknown opponent")
            print("        g=revealed good, e=revealed evil, X=exit")
        print()


# Setup helper functions
def get_default_setup(player: str) -> List[Dict]:
    """
    Get default piece arrangement for a player.
    
    Args:
        player: '1' or '2'
    
    Returns:
        List of 8 pieces with 'row', 'col', 'type' (columns 1-4 only)
    """
    if player == '1':
        # Player 1 default setup (rows 0-1, cols 1-4)
        return [
            {'row': 0, 'col': 1, 'type': 'good'},
            {'row': 0, 'col': 2, 'type': 'good'},
            {'row': 0, 'col': 3, 'type': 'evil'},
            {'row': 0, 'col': 4, 'type': 'evil'},
            {'row': 1, 'col': 1, 'type': 'good'},
            {'row': 1, 'col': 2, 'type': 'good'},
            {'row': 1, 'col': 3, 'type': 'evil'},
            {'row': 1, 'col': 4, 'type': 'evil'},
        ]
    else:  # player == '2'
        # Player 2 default setup (rows 4-5, cols 1-4)
        return [
            {'row': 4, 'col': 1, 'type': 'good'},
            {'row': 4, 'col': 2, 'type': 'good'},
            {'row': 4, 'col': 3, 'type': 'evil'},
            {'row': 4, 'col': 4, 'type': 'evil'},
            {'row': 5, 'col': 1, 'type': 'good'},
            {'row': 5, 'col': 2, 'type': 'good'},
            {'row': 5, 'col': 3, 'type': 'evil'},
            {'row': 5, 'col': 4, 'type': 'evil'},
        ]


def create_custom_setup(player: str, good_positions: List[Tuple[int, int]],
                       evil_positions: List[Tuple[int, int]]) -> List[Dict]:
    """
    Create a custom piece arrangement.

    Args:
        player: '1' or '2'
        good_positions: List of (row, col) tuples for good ghosts (must be 4, cols 1-4)
        evil_positions: List of (row, col) tuples for evil ghosts (must be 4, cols 1-4)

    Returns:
        List of 8 pieces with 'row', 'col', 'type'

    Example:
        setup = create_custom_setup('1',
                                   [(0, 1), (0, 2), (1, 1), (1, 2)],  # good ghosts
                                   [(0, 3), (0, 4), (1, 3), (1, 4)])  # evil ghosts
    """
    if len(good_positions) != 4 or len(evil_positions) != 4:
        raise ValueError("Must have exactly 4 good and 4 evil positions")

    # Validate setup area
    valid_rows = [0, 1] if player == '1' else [4, 5]
    valid_cols = [1, 2, 3, 4]
    all_positions = good_positions + evil_positions

    for row, col in all_positions:
        if row not in valid_rows:
            raise ValueError(f"Invalid row {row} for player {player}. Must be {valid_rows}")
        if col not in valid_cols:
            raise ValueError(f"Invalid column {col}. Must be in {valid_cols}")

    # Check for duplicate positions
    if len(set(all_positions)) != 8:
        raise ValueError("Positions must be unique")

    setup = []
    for row, col in good_positions:
        setup.append({'row': row, 'col': col, 'type': 'good'})
    for row, col in evil_positions:
        setup.append({'row': row, 'col': col, 'type': 'evil'})

    return setup


def manual_setup(player: str) -> List[Dict]:
    """
    Interactive manual setup - place your ghosts!
    
    Args:
        player: '1' or '2'
    
    Returns:
        List of 8 pieces with 'row', 'col', 'type'
    """
    print(f"\n🎮 GHOST SETUP for Player {player}")
    print("=" * 50)
    
    if player == '1':
        print("Your setup area: Rows 0-1, Columns 1-4")
        valid_rows = [0, 1]
    else:
        print("Your setup area: Rows 4-5, Columns 1-4")
        valid_rows = [4, 5]
    
    valid_cols = [1, 2, 3, 4]
    
    print("\nYou need to place:")
    print("  - 4 GOOD ghosts (these win by reaching opponent's exits)")
    print("  - 4 EVIL ghosts (if opponent captures all of these, you win!)")
    print("\nEnter positions as: row,col type (e.g., '0,1 good' or '1,3 evil')")
    print("Type 'default' to use default setup")
    print()
    
    setup = []
    good_count = 0
    evil_count = 0
    used_positions = set()
    
    while len(setup) < 8:
        remaining_good = 4 - good_count
        remaining_evil = 4 - evil_count
        
        print(f"\nPiece {len(setup) + 1}/8 - Need {remaining_good} good, {remaining_evil} evil")
        
        try:
            inp = input(f"Enter position and type (e.g., '{valid_rows[0]},1 good'): ").strip().lower()
            
            if inp == 'default':
                return get_default_setup(player)
            
            parts = inp.split()
            if len(parts) != 2:
                print("❌ Invalid format! Use: row,col type")
                continue
            
            pos_part, type_part = parts
            row, col = map(int, pos_part.split(','))
            
            if row not in valid_rows:
                print(f"❌ Invalid row! Must be {' or '.join(map(str, valid_rows))}")
                continue
            
            if col not in valid_cols:
                print(f"❌ Invalid column! Must be 1, 2, 3, or 4 (not 0 or 5)")
                continue
            
            if (row, col) in used_positions:
                print("❌ Position already used!")
                continue
            
            if type_part not in ['good', 'evil']:
                print("❌ Type must be 'good' or 'evil'")
                continue
            
            if type_part == 'good' and good_count >= 4:
                print("❌ Already have 4 good ghosts!")
                continue
            
            if type_part == 'evil' and evil_count >= 4:
                print("❌ Already have 4 evil ghosts!")
                continue
            
            setup.append({'row': row, 'col': col, 'type': type_part})
            used_positions.add((row, col))
            
            if type_part == 'good':
                good_count += 1
            else:
                evil_count += 1
            
            print(f"✅ Placed {type_part} ghost at ({row}, {col})")
            
        except (ValueError, IndexError):
            print("❌ Invalid input! Use format: row,col type")
        except KeyboardInterrupt:
            print("\n\n Using default setup...")
            return get_default_setup(player)
    
    print("\n✅ Setup complete!")
    return setup

print("✅ GhostsGame class and setup helpers loaded")

def manual_player_solver(game: GhostsGame) -> List:
    """
    Interactive manual player - YOU choose everything!
    Handles both setup and playing phases.
    """
    # SETUP PHASE
    if game.is_setup_phase() and not game.setup_complete():
        game.print_board()
        return manual_setup(game.my_player)
    
    # PLAYING PHASE
    game.print_board()
    
    moves = game.get_valid_moves()
    
    if not moves:
        print("No valid moves available!")
        return None
    
    print(f"\n🎮 YOUR TURN (Player {game.my_player})!")
    print("\nYour pieces and valid moves:")
    
    # Group moves by piece
    piece_moves = {}
    for move in moves:
        piece_id = move[0]
        if piece_id not in piece_moves:
            piece_moves[piece_id] = []
        piece_moves[piece_id].append(move)
    
    # Display moves
    move_list = []
    for piece_id, pmoves in piece_moves.items():
        piece = None
        for p in game.get_my_pieces():
            if p['id'] == piece_id:
                piece = p
                break
        
        if piece:
            print(f"\n  Ghost {piece_id} ({piece['type']}) at ({piece['row']}, {piece['col']}):")
            for move in pmoves:
                idx = len(move_list)
                move_list.append(move)
                
                # Check if capturing
                occupant = game.get_piece_at(move[1], move[2])
                if occupant:
                    print(f"    {idx}: Move to ({move[1]}, {move[2]}) [CAPTURE opponent ghost]")
                else:
                    print(f"    {idx}: Move to ({move[1]}, {move[2]})")
    
    while True:
        try:
            choice = input("\nEnter move number (or 'q' to quit): ").strip()
            
            if choice.lower() == 'q':
                raise KeyboardInterrupt()
            
            idx = int(choice)
            if 0 <= idx < len(move_list):
                return move_list[idx]
            else:
                print(f"❌ Invalid index! Choose 0-{len(move_list)-1}")
        
        except ValueError:
            print("❌ Invalid input! Enter a number.")
        except KeyboardInterrupt:
            print("\n👋 Thanks for playing!")
            raise

print("✅ Setup and play functions loaded")