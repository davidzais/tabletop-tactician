from tabletop_tactician.models.profiles import  WeaponType, CombatMatchup
from tabletop_tactician.combat_mechanics.damage import unit_damage
from tabletop_tactician.reference_data.roster import Army

def build_combat_matchups(attacking_army: Army, defending_army: Army) -> list[CombatMatchup]:   
    combat_matchups: list[CombatMatchup] = []
    for attacker in attacking_army.units:
       for defender in defending_army.units:           
           for phase in (WeaponType.RANGED, WeaponType.MELEE):
               damage = unit_damage(attacker_unit=attacker, target_unit=defender, attacker_faction_id=attacking_army.faction_id, defender_faction_id=defending_army.faction_id, phase=phase)               
               current_matchup = CombatMatchup(attacker=attacker.id, defender=defender.id, combat_phase=phase, damage=damage)
               combat_matchups.append(current_matchup)
    return combat_matchups