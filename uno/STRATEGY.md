# UNO AI – Current Strategy Explanation (`my_agent`)

Our current `my_agent` is a **simple heuristic-based UNO bot**.  
It does **not** simulate future turns or use recursion. Instead, it:

1. Gets all **valid moves** from the game.
2. If no card can be played, it **draws 1 card**.
3. Otherwise, it **scores every playable move** and chooses the highest-scoring one
   (breaking ties randomly).

---

## What information the agent uses

From the `game` object it reads:

- **Your hand**: `game.get_my_hand()`
- **All players’ hand sizes**: `game.get_hand_sizes()`
- **Current active color**: `game.get_current_color()`
- **Valid moves right now**: `game.get_valid_moves()`

It also counts how many cards you have of each color
(red/blue/green/yellow) to know your **strongest color**.

---

## High-level priorities

### 1. Always play if possible
If there is at least one valid “play” move, the agent will play something
instead of drawing.

### 2. Reduce hand size quickly
Every playable move gets a base score for shrinking your hand.
Fewer cards = closer to winning.

### 3. Prefer your majority color
For normal (non-wild) cards, the agent adds points if the move plays a color
you hold many of.  
This helps keep future turns playable.

It also gives a small bonus if the card matches the **current color**,
because that avoids handing color control to opponents.

### 4. Use action cards to block near-winning opponents
Cards with values:
- `draw2`
- `skip`
- `reverse`

get extra points, since they disrupt opponents.

If **any opponent has 2 or fewer cards**, these action cards get a *big* bonus,
because stopping someone about to win matters more than saving power cards.

### 5. Save wild cards unless needed now
Wild cards are valuable late-game, so:

- If we have **other (non-wild) playable cards**
- AND we still have a decent hand size (>3)
- AND no opponent is close to winning (>2 cards)

then wild moves get a penalty.

Wilds are only favored when:
- they help us win soon, or
- an opponent is about to win.

When a wild is played, the agent chooses the **color we have the most of**
(using the expanded wild moves from `get_valid_moves()`).

---

## How the scoring works (summary)

For each playable move:

1. **Instant win bonus**  
   If playing the card leaves us with 0 cards, it gets a huge score boost.

2. **Hand size bonus**  
   Smaller resulting hand → higher score.

3. **Action card bonus**  
   `draw2/skip/reverse` are strong; even stronger if an opponent is low.

4. **Color bonus**
   - Non-wild: prefer colors we already hold a lot of.
   - Wild: prefer choosing our majority color.

5. **Wild penalty (situational)**  
   Penalize wilds early if safer plays exist.

Finally, the bot returns the **best-scoring valid move**.

---

## Complexity

Let **H = number of cards in our hand**.

- We evaluate each playable move once → **O(H)** time per turn.
- We store a color counter → **O(H)** memory.

So the agent is fast, simple, and fully within the assignment’s expectations.
