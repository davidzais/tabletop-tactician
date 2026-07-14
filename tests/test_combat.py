import pytest
from tabletop_tactician.models.profiles import WeaponType
from tabletop_tactician.reference_data.reference import weapon_raw, unit_raw
from tabletop_tactician.combat_mechanics.damage import weapon_damage, unit_damage
from tabletop_tactician.reference_data.roster import Army
from tabletop_tactician.combat_mechanics.threat_matrix import build_combat_matchups
from tabletop_tactician.reference_data.roster import FieldedUnit, Wargear

def test_pistol_rule_suppresses_pistols():
  
    # 1 rifle + 5 pistols → the rule should fire the rifle + (5 − 1) = 4 pistols
    # even though one model of the 5 has a pistol and a rifle, the rifle does more damage so we are going to assume
    # the player will be fireing the rifle, not the pistol
    attacker = FieldedUnit(
        id="intercessor-squad",
        model_count=5,
        wargear=[Wargear(id="bolt-rifle", count=1), Wargear(id="bolt-pistol", count=5), Wargear(id="close-combat-weapon", count=5)],
    )
   
    attacker_faction = "adeptus-astartes"

    target = FieldedUnit(id="boyz", model_count=10, wargear=[])   # only .id is used as the crunch target    
    target_unit = unit_raw(target.id)


    rifle = weapon_raw(weapon_id="bolt-rifle", faction_id=attacker_faction)
    pistol = weapon_raw(weapon_id="bolt-pistol", faction_id=attacker_faction)
    expected = weapon_damage(weapon_raw_dict=rifle, target_raw_dict=target_unit, models_firing=1)
    expected +=  weapon_damage(weapon_raw_dict=pistol, target_raw_dict=target_unit, models_firing=4)

    assert unit_damage(attacker_unit=attacker, target_unit=target, attacker_faction_id=attacker_faction, phase=WeaponType.RANGED) == pytest.approx(expected)

    melee_weapon = weapon_raw(weapon_id="close-combat-weapon", faction_id=attacker_faction)
    expected_melee = weapon_damage(weapon_raw_dict=melee_weapon, target_raw_dict=target_unit, models_firing=5)   
    
    assert unit_damage(attacker_unit=attacker, target_unit=target, attacker_faction_id=attacker_faction, phase=WeaponType.MELEE) == pytest.approx(expected_melee)

    
def test_matchup(army_a: Army, army_b: Army):
    attacking_army = army_a    
    defending_army = army_b
    matchups = build_combat_matchups(attacking_army=attacking_army, defending_army=defending_army)
    
    assert len(matchups) == len(attacking_army.units) * len(defending_army.units) * 2


    attacking_army = army_b
    defending_army = army_a
    matchups = build_combat_matchups(attacking_army=attacking_army, defending_army=defending_army)
    
    assert len(matchups) == len(attacking_army.units) * len(defending_army.units) * 2
