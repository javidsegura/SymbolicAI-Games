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
