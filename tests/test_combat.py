import pytest
from tabletop_tactician.models.profiles import WeaponType
from tabletop_tactician.reference_data.dataset import  weapon_damage, weapon_raw, unit_damage, unit_raw

from tabletop_tactician.combat_mechanics.threat_matrix import build_combat_matchups





def test_unit_damage(space_marines_army, orks_army):
    _check(space_marines_army[0], orks_army[0] )
    _check( orks_army[0], space_marines_army[0] )
        
   
def _check(attacking, defending ):
    #NOTE: the reason we do this here is because weapon_damage needs the wh40kdc representation of the army in the 
    # crunch call, and what we have is an actual roster in defending_unit. two differnt things, so we have to get the id of the unit in the roster
    # so the library can look it up to get the representation it needs to call crunch
    defending_army_raw = unit_raw(defending["ref"]["id"])

   
    expected: float = 0.0
    for wg in attacking["wargear"]:
        w = weapon_raw(wg["ref"]["id"])
        if w["type"] != WeaponType.RANGED:
            continue
        expected += weapon_damage(w, defending_army_raw, models_firing=wg["count"])   # real per-weapon count
        
    assert unit_damage(attacking,  defending, WeaponType.RANGED) == pytest.approx(expected)

    expected_melee =  0.0 
    for wg in attacking["wargear"]:
        w = weapon_raw(wg["ref"]["id"])
        if w["type"] != WeaponType.MELEE:
            continue
        expected_melee += weapon_damage(w, defending_army_raw, models_firing=wg["count"])
    
    assert unit_damage(attacking, defending, WeaponType.MELEE) == pytest.approx(expected_melee)


def test_matchup(space_marines_army, orks_army):
    attacking_army = space_marines_army
    defending_army = orks_army
    matchups = build_combat_matchups(attacking_army, defending_army)
    
    assert len(matchups) == len(attacking_army) * len(defending_army) * 2
