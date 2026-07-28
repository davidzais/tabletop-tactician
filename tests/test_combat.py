import pytest
from tabletop_tactician.models.profiles import WeaponType
from tabletop_tactician.reference_data.reference import (
    weapon_raw,
    unit_raw,
    wound_pool,
    describe_buff,
    merge_leaders_with_units,
)
from tabletop_tactician.combat_mechanics.damage import weapon_damage, unit_damage, pistol_damage
from tabletop_tactician.reference_data.roster import Army
from tabletop_tactician.combat_mechanics.threat_matrix import build_combat_matchups, unique_labels
from tabletop_tactician.reference_data.roster import FieldedUnit, Wargear, UnitComposition


def test_pistol_rule_suppresses_pistols():

    # 1 rifle + 5 pistols → the rule should fire the rifle + (5 − 1) = 4 pistols
    # even though one model of the 5 has a pistol and a rifle, the rifle does more damage so we are going to assume
    # the player will be fireing the rifle, not the pistol
    attacker = FieldedUnit(
        id="intercessor-squad",
        name="Intercessor Squad",
        model_count=5,
        wargear=[
            Wargear(id="bolt-rifle", count=1),
            Wargear(id="bolt-pistol", count=5),
            Wargear(id="close-combat-weapon", count=5),
        ],
    )

    attacker_faction = "adeptus-astartes"
    defender_faction = "orks"

    target = FieldedUnit(id="boyz", name="Boyz", model_count=10, wargear=[])  # only .id is used as the crunch target
    target_unit = unit_raw(target.id)

    rifle = weapon_raw(weapon_id="bolt-rifle", faction_id=attacker_faction)
    pistol = weapon_raw(weapon_id="bolt-pistol", faction_id=attacker_faction)
    expected = weapon_damage(
        weapon_raw_dict=rifle,
        target_raw_dict=target_unit,
        defender_faction_id=defender_faction,
        phase=WeaponType.RANGED,
        models_firing=1,
        target_unit_leaders=[],
    )
    expected += weapon_damage(
        weapon_raw_dict=pistol,
        target_raw_dict=target_unit,
        defender_faction_id=defender_faction,
        phase=WeaponType.RANGED,
        models_firing=4,
        target_unit_leaders=[],
    )

    assert unit_damage(
        attacker_unit=attacker,
        target_unit=target,
        attacker_faction_id=attacker_faction,
        defender_faction_id=defender_faction,
        phase=WeaponType.RANGED,
    ) == pytest.approx(expected)

    melee_weapon = weapon_raw(weapon_id="close-combat-weapon", faction_id=attacker_faction)
    expected_melee = weapon_damage(
        weapon_raw_dict=melee_weapon,
        target_raw_dict=target_unit,
        defender_faction_id=defender_faction,
        phase=WeaponType.RANGED,
        models_firing=5,
        target_unit_leaders=[],
    )

    assert unit_damage(
        attacker_unit=attacker,
        target_unit=target,
        attacker_faction_id=attacker_faction,
        defender_faction_id=defender_faction,
        phase=WeaponType.MELEE,
    ) == pytest.approx(expected_melee)


def test_matchup(army_a: Army, army_b: Army):
    attacking_army = army_a
    defending_army = army_b
    matchups = build_combat_matchups(attacking_army=attacking_army, defending_army=defending_army)

    assert len(matchups) == len(attacking_army.units) * len(defending_army.units) * 2

    attacking_army = army_b
    defending_army = army_a
    matchups = build_combat_matchups(attacking_army=attacking_army, defending_army=defending_army)

    assert len(matchups) == len(attacking_army.units) * len(defending_army.units) * 2


def test_wound_pool():
    # two profiles + composition → itemize: 9×1 + 1×2 = 11
    # produces the following 2 profiles
    # .[{'Ld': 7, 'M': 6, 'OC': 2, 'Sv': 5, 'T': 5, 'W': 1, 'invuln_sv': None, 'name': 'Boy'},
    #  {'Ld': 7, 'M': 6, 'OC': 2, 'Sv': 5, 'T': 5, 'W': 2, 'invuln_sv': None, 'name': 'Boss Nob'}]
    # so a unit of 9 boyz and 1 Nob 9×1 + 1×2 = 11 wounds
    boyz = FieldedUnit(
        id="boyz",
        name="Boyz",
        model_count=10,
        wargear=[],
        composition=[UnitComposition("Boss Nob", 1), UnitComposition("Boy", 9)],
    )
    assert wound_pool(boyz) == 11

    # one profile → model_count × W, composition irrelevant: 5×2 = 10
    nobz = FieldedUnit(id="nobz", name="Nobz", model_count=5, wargear=[], composition=[])
    assert wound_pool(nobz) == 10

    # two profiles, no composition → model_count × min(W): 11 × min(1,2) = 11
    gretchin = FieldedUnit(id="gretchin", name="Gretchin", model_count=11, wargear=[], composition=[])
    assert wound_pool(gretchin) == 11


def test_unique_labels():
    units = [
        FieldedUnit(id="boyz", name="Boyz", model_count=10, wargear=[]),
        FieldedUnit(id="boyz", name="Boyz", model_count=10, wargear=[]),
        FieldedUnit(id="warboss", name="Warboss", model_count=5, wargear=[], composition=[]),
    ]
    assert unique_labels(units) == ["boyz #1", "boyz #2", "warboss"]


def test_pistol_damage_allocation():
    plasma, bolt = 0.5, 0.1
    # budget 2, plasma better -> fire 2 plasma, bolts sit out
    assert pistol_damage([(plasma, 4), (bolt, 8)], 2) == 2 * plasma
    # budget 3, only 1 plasma -> spill into 2 bolt
    assert pistol_damage([(plasma, 1), (bolt, 8)], 3) == plasma + 2 * bolt
    # bolt listed FIRST but plasma better -> ranking still fires plasma first
    assert pistol_damage([(bolt, 8), (plasma, 1)], 3) == plasma + 2 * bolt
    # nothing fires
    assert pistol_damage([(plasma, 4)], 0) == 0.0


@pytest.mark.parametrize(
    "buff, expected",
    [
        ({"type": "feel-no-pain", "threshold": 5}, "Feel No Pain 5+"),
        ({"type": "invulnerable-save", "threshold": 2}, "Invulnerable Save 2+"),
        ({"type": "hit-mod", "value": -1}, "-1 to be hit"),
        ({"type": "toughness-mod", "value": 1}, "+1 Toughness"),
        ({"type": "damage-reduction", "value": 1}, "Damage -1"),
        ({"type": "wound-mod", "value": -1}, "-1 to be wounded"),
        ({"type": "some-future-threshold-thing", "threshold": 3}, "Some Future Threshold Thing"),
    ],
)
def test_describe_buff(buff, expected):
    assert describe_buff(buff) == expected


def test_merge_leaders_with_unit():
    boyz = FieldedUnit(
        id="boyz",
        name="Boyz",
        model_count=10,
        wargear=[Wargear(id="choppa", count=20)],
        leaders=["painboy"],
        points=150,
        wounds=21,
        composition=[UnitComposition("Boss Nob", 1), UnitComposition("Boy", 19)],
    )
    painboy = FieldedUnit(
        id="painboy",
        name="Painboy",
        model_count=1,
        wargear=[Wargear(id="power-klaw", count=1)],
        points=80,
        wounds=3,
        composition=[UnitComposition("Painboy", 1)],
        leader_attachment={"bodyguard_ref": {"raw_name": "Boyz"}, "role": "leader", "provisional": False},
    )

    army = Army(faction_id="Orks", units=[boyz, painboy])
    merged = merge_leaders_with_units(army=army)
    unit = merged.units[0]
    # check that there is only one unit after the merge
    assert len(merged.units) == 1
    assert unit.leaders[0] == "painboy"
    assert unit.name == "Boyz with ( Painboy )"
    assert unit.points == boyz.points + painboy.points
    assert unit.wounds == wound_pool(boyz) + wound_pool(painboy)
    assert unit.wargear == [Wargear(id="choppa", count=20), Wargear(id="power-klaw", count=1)]
