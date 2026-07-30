"""Build units by hand and print their matchup damage.

A dev/exploration view — NOT a test. `show_matrix.py` reads whole rosters from
files; this one lets you type a unit out by hand so you can poke at a single
"what if" (swap a weapon, attach a different leader, change the model count) and
see the damage move, without needing a roster export.

To try something different: edit the units in build_armies() below and re-run.

    python scripts/show_units.py
"""

from tabletop_tactician.combat_mechanics.threat_matrix import build_combat_matchups
from tabletop_tactician.models.profiles import CombatMatchup
from tabletop_tactician.reference_data.roster import (
    Army,
    FieldedUnit,
    UnitComposition,
    Wargear,
)


def build_armies() -> tuple[Army, Army]:
    """The two hand-built armies to compare. Edit freely — this is a scratchpad.

    Note on leaders: to attach a character, give the squad a `leaders=[...]` list
    of the leader's id, and give the leader a `leader_attachment` pointing back at
    the squad. build_combat_matchups folds them together for you.
    """
    canoness = FieldedUnit(
        id="canoness",
        name="Canoness",
        model_count=1,
        wounds=4,
        wargear=[
            Wargear(id="bolt-pistol-canoness", count=1),
            Wargear(id="hallowed-chainsword", count=1),
        ],
        leader_attachment={"bodyguard_ref": {"id": "battle-sisters-squad"}},
    )
    sisters = FieldedUnit(
        id="battle-sisters-squad",
        name="Battle Sisters Squad",
        model_count=20,
        wounds=1,
        wargear=[
            Wargear(id="bolt-pistol", count=20),
            Wargear(id="chainsword-battle-sisters-squad", count=20),
        ],
        leaders=["canoness"],
    )
    sisters_army = Army(faction_id="adepta-sororitas", units=[canoness, sisters])

    painboy = FieldedUnit(
        id="painboy",
        name="Painboy",
        model_count=1,
        wounds=3,
        wargear=[Wargear(id="power-klaw", count=1)],
        composition=[UnitComposition("Painboy", 1)],
        leader_attachment={"bodyguard_ref": {"id": "boyz"}},
    )
    boyz = FieldedUnit(
        id="boyz",
        name="Boyz",
        model_count=20,
        wounds=21,
        wargear=[
            Wargear(id="choppa", count=19),
            Wargear(id="slugga", count=20),
            Wargear(id="big_choppa", count=1),
        ],
        leaders=["painboy"],
        composition=[UnitComposition("Boss Nob", 1), UnitComposition("Boy", 19)],
    )
    orks_army = Army(faction_id="orks", units=[painboy, boyz])

    return sisters_army, orks_army


def print_matchups(matchups: list[CombatMatchup]) -> None:
    header = f"{'Attacker':<40}{'Defender':<40}{'Phase':<10}{'Est. Damage':>12}"
    print(header)
    for cm in matchups:
        print(f"{cm.attacker:<40}{cm.defender:<40}{cm.combat_phase.value:<10}{cm.damage:>12.2f}")


def main() -> None:
    attacker, defender = build_armies()

    # both directions: A hitting B, then B hitting A
    matchups = build_combat_matchups(attacker, defender)
    matchups += build_combat_matchups(defender, attacker)

    print_matchups(matchups)


if __name__ == "__main__":
    main()
