# GHOSTS 
## GRADING
Grading (90pts + 30pts total) (20% of total grade)
● 90pts for the games, with AI using concepts from class
○ 30pts for game 1
○ 30pts for game 2 (harder)
○ 30pts for game 3 (partial information or stochastic game)
● Game points are awarded as follows:
○ 5pts if the AI can play the game
○ 15pts if the AI can win against a random player (mostly)
○ 5pts if the AI wins any matches in the tournament
○ 5pts if the AI wins all matches in the tournament
○ No points are awarded if not using the concepts from class (e.g. if using ML)
● 30pts for final presentations
○ 10pts group effort
○ 20pts individual effort (question answering)

## GAME EXPLANATION
- Two player game
- Grid is usually 6x6
- Each player has 8 ghosts, 4 good and 4 evil (only owner knows their type)
 - Arranged from col 1 to col 4
 - Arranged from first to second row  
 - Actions 
   - One orthogonal (no diagonal) movement per time
   - Capture: move onto their cell and reveal their type
- Win conditions:
   - Capture all of the opponents Good Ghosts
   - Move one of your opponents good ghotsts into the oppenets exit corner 
- Lose condition: 
  - Above stuff happens to you 
  - You capture all of the opponents' evil ghosts 

## STRATEGIES
- Early Game (Turns 1-8)
  - Setup Analysis
    - Track which ghosts move forward aggressively (likely good)
    - Which stay back defensively (likely evil or protecting good)
  - Probing Moves
    - Force opponent to make revealing choices
    - Create situations where they must move suspicious ghosts
  - Initial Bluffing
    - Move 1-2 evil ghosts forward aggressively
    - Move good ghosts cautiously to appear evil

- Mid Game (Turns 9-20)
  - Bayesian Belief Updating
    - Key insight: Track probability each ghost is good/evil
    - Update after every opponent move using behavioral patterns:
      - Aggressive forward movement → likely good (70-80%)
      - Defensive positioning → likely evil (60-70%)
      - Protection of another ghost → protector likely evil, protected likely good
  - Calculated Captures
    - Only capture when P(good) > 70-80%
    - Avoid captures unless strategically necessary
  - Zone Control
    - Control center to limit opponent options
    - Create "safe corridors" for your good ghosts

- Late Game (Turns 20+)
  - Exit Rush
    - Once good ghosts identified, push toward opponent exit
    - Use evil ghosts as blockers/sacrifices
  - Defensive Positioning
    - Block opponent's suspected good ghosts from your exit
    - Force them into capture-or-retreat dilemmas

## ALGORITHMS TO USE
- Minimax with Expectimax 
- Alpha-beta pruning
- Probabilistic reasoning about opponent's piece types (updates probability everytime based on user modification)
- Custom heuristics
- Advanced strategies (see above)

## PRUNING

## HEURISTICS 
[Read](https://claude.ai/share/d01c4479-7e4d-4c46-bb3c-3749e6e56373)

## GENERAL IDEAS TO TRY
Ideas to try:
1. Consider not using the same setup strategy all the time
2. Advance good ghosts toward exits (row 5 for P1, row 0 for P2)
3. ... but try not to expose them to easy captures or reveal them
4. Use evil ghosts as blockers or to safely capture
5. Implement expectiminimax for handling hidden information
6. Use probabilistic reasoning about unrevealed ghosts
7. How to get a better opening start
8. Can the game be made more efficient to run?
9. Can we use MCTS

## PLAN
# Strategic Implementation Order for Tournament Success

Given your goal is to **win the tournament**, here's the optimal order:

## 🎯 Recommended Implementation Path

### **Phase 1: Basic Minimax + Simple Heuristic** (Week 1)
**Goal**: Get the 5pts for "AI can play" + most of the 15pts for "beats random player"

```python
# Simple heuristic to start
def evaluate(state):
    score = 0
    # Count your pieces vs opponent pieces
    score += 10 * (my_ghosts_alive - opp_ghosts_alive)
    # Distance to opponent exit (for good ghosts)
    score -= sum(distance_to_exit(g) for g in my_good_ghosts)
    return score
```

**Why first?**
- ✅ Gets you playing immediately
- ✅ Even shallow minimax (depth 3-4) crushes random players
- ✅ Validates your game logic is correct
- ✅ Gives you a baseline to test improvements against

---

### **Phase 2: Alpha-Beta Pruning** (Week 1-2)
**Goal**: Search deeper (depth 6-8 instead of 3-4)

**Why second?**
- ✅ **Biggest bang for buck** - literally searches 100x faster!
- ✅ Minimal code change (~10 lines)
- ✅ Deeper search = much stronger play
- ✅ Essential for tournament (you'll timeout without it)

```python
def minimax_alphabeta(state, depth, alpha, beta, maximizing):
    if depth == 0:
        return evaluate(state)
    
    if maximizing:
        max_eval = -infinity
        for move in get_moves(state):
            eval = minimax_alphabeta(apply(state, move), depth-1, alpha, beta, False)
            max_eval = max(max_eval, eval)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break  # Prune!
        return max_eval
    else:
        # Similar for minimizing
```

**Testing**: Your AI should now search 3-4x deeper in same time!

---

### **Phase 3: Better Heuristic** (Week 2)
**Goal**: Win more tournament matches (the 5pt bonuses)

**Why third?**
- ✅ Now that you search deep, evaluation quality matters MORE
- ✅ This is what separates good AIs from great ones
- ✅ Easier to debug with working minimax + pruning

```python
def evaluate_v2(state, belief_state):
    score = 0
    
    # 1. Material count (weighted by certainty)
    for ghost in my_ghosts:
        if ghost.revealed:
            score += 50 if ghost.is_good else 20
        else:
            score += 35  # Average value
    
    # 2. Positional advantage
    for ghost in my_good_ghosts:
        score -= 5 * manhattan_distance(ghost, opponent_exit)
        if is_protected(ghost):
            score += 10
    
    # 3. Threats and captures
    for opp_ghost in opponent_ghosts:
        if can_capture(opp_ghost):
            # Only value if likely good!
            prob_good = belief_state[opp_ghost]['good']
            score += 30 * prob_good - 100 * (1 - prob_good)
    
    # 4. Mobility
    score += 2 * len(get_legal_moves(state))
    
    return score
```

**At this point you should beat random 95%+ and win some tournament matches!**

---

### **Phase 4: Expectimax (The Game-Changer)** (Week 3)
**Goal**: Dominate the tournament

**Why fourth (not earlier)?**
- ❌ Expectimax is COMPLEX - need solid foundation first
- ❌ Bugs are harder to debug without working minimax
- ✅ But THIS is what wins tournaments in imperfect information games!
- ✅ Your pruning experience makes this easier

**Implementation Strategy:**

```python
def expectimax(state, depth, alpha, beta, is_max_node, belief_state):
    if depth == 0:
        return evaluate(state, belief_state)  # Note: uses beliefs!
    
    if is_max_node:
        # Your turn - pick best move
        return max_node(state, depth, alpha, beta, belief_state)
    else:
        # Opponent turn - expectation over ghost configs
        return chance_node(state, depth, belief_state)

def chance_node(state, depth, belief_state):
    # CRITICAL: Don't enumerate all configs!
    # Use Monte Carlo sampling
    
    total_value = 0
    num_samples = 10  # Start small, tune later
    
    for _ in range(num_samples):
        # Assign ghost types based on belief probabilities
        config = sample_configuration(belief_state)
        temp_state = apply_ghost_types(state, config)
        
        # Opponent plays optimally under this config
        value = max_node_opponent(temp_state, depth-1, belief_state)
        total_value += value
    
    return total_value / num_samples
```

**Critical Addition: Belief Tracking**

```python
class BeliefState:
    def __init__(self):
        # Initially uniform: each ghost 50% good, 50% evil
        self.beliefs = {
            ghost: {'good': 0.5, 'evil': 0.5} 
            for ghost in opponent_ghosts
        }
    
    def update(self, ghost, move):
        """Update beliefs based on opponent's move"""
        # If ghost moved toward our exit
        if is_aggressive(move):
            self.beliefs[ghost]['good'] *= 1.5  # More likely good
        
        # If ghost retreated when threatened
        elif is_defensive(move):
            self.beliefs[ghost]['evil'] *= 1.3  # More likely evil
        
        # Normalize probabilities
        self._normalize(ghost)
    
    def reveal(self, ghost, actual_type):
        """Ghost was captured - update to certainty"""
        self.beliefs[ghost]['good'] = 1.0 if actual_type == 'good' else 0.0
        self.beliefs[ghost]['evil'] = 1.0 - self.beliefs[ghost]['good']
```

---

## 📊 Expected Tournament Performance by Phase

| Phase | Can Play (5pts) | Beat Random (15pts) | Any Wins (5pts) | All Wins (5pts) | Total |
|-------|----------------|---------------------|-----------------|-----------------|-------|
| Phase 1 | ✅ 5 | ✅ 12-15 | ❌ 0-2 | ❌ 0 | **17-22pts** |
| Phase 2 | ✅ 5 | ✅ 15 | ✅ 3-5 | ❌ 0 | **23-25pts** |
| Phase 3 | ✅ 5 | ✅ 15 | ✅ 5 | 🟡 0-3 | **25-28pts** |
| Phase 4 | ✅ 5 | ✅ 15 | ✅ 5 | ✅ 5 | **30pts** 🏆 |

---

## ⚠️ Common Pitfalls (Learn from Others' Mistakes!)

### ❌ Starting with Expectimax
- You'll spend 2 weeks debugging
- Won't have time to tune heuristics
- Might not even beat random players!

### ❌ Over-engineering Heuristics Early
- Fancy heuristics mean nothing at depth 2
- Search depth > evaluation complexity (at first)

### ❌ Skipping Alpha-Beta
- Your AI will timeout in tournaments
- Can't search deep enough to be competitive

---

## 🎯 Week-by-Week Timeline (3 weeks total)

### **Week 1: Foundation**
- Days 1-2: Implement basic minimax + simple heuristic
- Days 3-4: Add alpha-beta pruning
- Days 5-7: Test, fix bugs, measure performance

**Checkpoint**: Beats random 90%+, searches to depth 6

---

### **Week 2: Polish**
- Days 1-3: Improve heuristic (add 3-4 features)
- Days 4-5: Add move ordering for better pruning
- Days 6-7: Test against classmates, identify weaknesses

**Checkpoint**: Wins some tournament matches

---

### **Week 3: Advanced**
- Days 1-3: Implement belief tracking system
- Days 4-5: Add expectimax with Monte Carlo sampling
- Days 6-7: Tune parameters, optimize performance

**Checkpoint**: Dominates tournament

---

## 🔧 Pro Tips for Tournament Day

1. **Iterative Deepening** (Add in Phase 2)
```python
def get_best_move(state, time_limit):
    best_move = None
    depth = 1
    
    while time_remaining() > 0.1:  # Keep 100ms buffer
        best_move = minimax(state, depth)
        depth += 1
    
    return best_move
```

2. **Opening Book** (Add in Phase 3)
- Pre-compute strong opening moves
- Saves time, guarantees good start

3. **Transposition Table** (Optional Phase 3)
- Cache previously evaluated positions
- Huge speedup in Ghosts (many transpositions)

4. **Time Management**
- Use 70% of time on early moves (more critical)
- Use 30% on late game (faster anyway)

---

## 🎓 Final Advice

**For winning the tournament:**

1. **Don't skip Phase 2** - Alpha-beta is MANDATORY
2. **Phase 3 heuristic features that matter most:**
   - Capture risk assessment (avoid evil ghosts!)
   - Exit distance for good ghosts
   - Protecting your good ghosts
3. **Phase 4 makes you elite** - but only if foundation is solid

**Start coding Phase 1 TODAY**. Get something working, then iterate. A working weak AI beats a theoretical strong AI every time!

Good luck! 🚀