"""Print the combat threat matrix for two rosters.

A dev/exploration view — NOT a test. Tests assert one known-good number and stay
silent; this shows the whole grid so you can eyeball whether the numbers look sane.

Usage:
    python scripts/show_matrix.py [attacker_roster.json] [defender_roster.json]

With no arguments it falls back to the test-fixture rosters.
"""

import sys
from pathlib import Path

from tabletop_tactician.reference_data.roster import Army, load_roster
from tabletop_tactician.combat_mechanics.threat_matrix import build_combat_matchups
from tabletop_tactician.models.profiles import CombatMatchup

ROSTERS = Path(__file__).parent.parent / "rosters" 


def load(path: Path) -> Army:
    return load_roster(path.read_text(encoding="utf-8"))


def main() -> None:
    args = sys.argv[1:]
    attacker_path = Path(args[0]) if len(args) > 0 else ROSTERS / "ba_1000_gw.txt"
    defender_path = Path(args[1]) if len(args) > 1 else ROSTERS / "orks_1000_gw.txt"

    attacker = load(attacker_path)
    defender = load(defender_path)

    matchups: list[CombatMatchup] = build_combat_matchups(attacker, defender)

    
    matchups2: list[CombatMatchup] = build_combat_matchups(defender, attacker)
    matchups += matchups2
    header = f"{'Attacker':<50}{'Defender':<50}{'Phase':<24}{'Est. Damage':>10}"
   
    print(header)
    print()

    for cm in matchups:
        print(f"{cm.attacker:<50}{cm.defender:<50}{cm.combat_phase:<24}{cm.damage:>10.2f}")
    

if __name__ == "__main__":
    main()