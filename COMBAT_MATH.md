# Combat Math — how expected damage is computed

This documents the probability model behind the damage numbers. The runtime math now lives inside
`wh40kdc.crunch` (our hand-rolled `combat_mechanics/combat.py` was retired — see `NOTES.md`), but the
*model* it implements is the one described here. Keeping it written down means the numbers are never a
black box.

## 1. Expected value, not simulation

We do **not** simulate dice. There are two ways to answer "how much damage does this do on average":

| Approach | How | Result |
|---|---|---|
| **Monte Carlo (simulation)** | Have the computer roll virtual dice thousands of times (using a random-number generator), then average the results | *Approximate*, noisy, gives a slightly different answer each run, needs many trials |
| **Closed-form expected value** ← we use this | Compute the probability-weighted average directly with arithmetic | *Exact*, deterministic, instant — same input always yields the same number |

The closed-form route is why the engine is a **deterministic source of truth**: the same matchup always
produces the same number, with no randomness to average out. It's also the "why not just ask ChatGPT"
answer — the odds are *computed*, not guessed.

**Expected value** is the definition everything rests on:

```
E[X] = Σ (outcome × probability of that outcome)
```

In plain words: go through every result the dice *could* give, multiply each result by how likely it is,
and add them all up. That weighted total **is** the long-run average. (The `Σ` just means "add up all of
these".)

For example, a fair d6: each face (1 through 6) is equally likely, with probability 1/6. So its expected
value is:

```
(1 × 1/6) + (2 × 1/6) + (3 × 1/6) + (4 × 1/6) + (5 × 1/6) + (6 × 1/6)
= (1 + 2 + 3 + 4 + 5 + 6) / 6
= 21 / 6
= 3.5
```

Because every face is equally likely here, the "probability-weighted" part collapses to a plain "add them
up and divide by how many" — but the weighting by probability is what the definition is really doing, and
it matters the moment the outcomes *aren't* equally likely (like hit/wound/save rolls, §2b).

## 2. The two "average dice roll" formulas

These are different tools and easy to confuse.

### (a) Mean of a single die — used when a stat is random (e.g. "Damage D6", "Attacks D3")

```
E[dN] = (1 + 2 + … + N) / N = (N + 1) / 2
```

- d6 → (1+2+3+4+5+6)/6 = 21/6 = **3.5**
- d3 → (1+2+3)/3 = 6/3 = **2**

The `(N+1)/2` shortcut is just the algebra of the sum: `1+2+…+N = N(N+1)/2`, divided by `N`.

### (b) Probability a d6 meets a target number N ("N+") — used for hit / wound / save rolls

```
P(roll ≥ N) = (7 − N) / 6
```

The faces that succeed are {N, N+1, …, 6}, which is `(7 − N)` of them, each worth 1/6.

| Need | P(success) |
|---|---|
| 2+ | 5/6 ≈ 0.833 |
| 3+ | 4/6 ≈ 0.667 |
| 4+ | 3/6 = 0.500 |
| 5+ | 2/6 ≈ 0.333 |
| 6+ | 1/6 ≈ 0.167 |

(Real dice clamp: a natural 1 always fails and a 6 always succeeds. `crunch` models this; our old
engine did not — a logged simplification.)

## 3. The funnel — one weapon's expected damage

Think of it as a **funnel**: every stage lets through only a *fraction* of what the stage before it
produced. A hit roll passes some of the attacks; a wound roll passes some of the hits; a failed save lets
some of those wounds through. Multiplying the fractions in a row is the same as shrinking the running
count step by step down the funnel — that's why the stages multiply:

```
expected_damage = Attacks × P(hit) × P(wound) × P(fail save) × Damage
```

| Stage | Target number N | Probability |
|---|---|---|
| Hit | `BS` (ranged) or `WS` (melee) | (7 − N) / 6 |
| Wound | from the Strength-vs-Toughness chart (§4) | (7 − N) / 6 |
| Fail save | effective save = `Sv − AP`, using the better of armour/invulnerable | 1 − (7 − N) / 6 |
| — | Attacks (A) and Damage (D) may themselves be dice → use §2(a) | × A × D |

**Worked example** — a weapon with 4 attacks, hitting on 3+, Strength 5 into Toughness 4 (so it wounds on
3+), against a 4+ save that AP −1 drops to a 5+, dealing 2 damage. Walk the count down the funnel:

- Start with **4** attacks.
- Hits on 3+ → 4/6 land → 4 × 0.667 = **2.67** hits.
- Wounds on 3+ → 4/6 of those → 2.67 × 0.667 = **1.78** wounds.
- The save now needs a 5+, which makes it only 2/6 of the time, so 4/6 **fail** → 1.78 × 0.667 = **1.19** get through.
- Each wound that gets through does 2 damage → 1.19 × 2 = **2.37** expected wounds.

Doing it in one line is the exact same arithmetic: `4 × (4/6) × (4/6) × (4/6) × 2 ≈ 2.37`. The step-by-step
version and the one-liner always agree — the funnel *is* the multiplication.

## 4. The wound roll — a chart, not a stat

The wound target number is not on the datasheet; it's derived from weapon **Strength (S)** vs target
**Toughness (T)**:

| Strength vs Toughness | Wound on |
|---|---|
| S ≥ 2 × T | 2+ |
| S > T | 3+ |
| S = T | 4+ |
| S < T | 5+ |
| S ≤ ½ × T | 6+ |

## 5. What we own vs. what the library owns

`wh40kdc.crunch` computes all of the above **plus** the things our old engine deferred: the nat-1/6 clamp,
dice-valued stats, models-killed caps, and abilities (Lethal Hits, Sustained Hits, Devastating Wounds,
Anti-X, Rapid Fire, Blast, Melta, Cover, Feel No Pain, re-rolls). What remains *ours* is the roll-up
(summing a unit's weapons per phase, incl. the pistol rule) and everything above the single-attack math:
the threat matrix, the agent, and the advice. See `NOTES.md` for the roll-up's remaining simplifications.
