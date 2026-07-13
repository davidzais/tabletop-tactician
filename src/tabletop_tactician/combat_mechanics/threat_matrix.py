from tabletop_tactician.models.profiles import  WeaponType, CombatMatchup
from tabletop_tactician.reference_data.dataset import unit_damage

def build_combat_matchups(attacking_army: list[dict], defending_army: list[dict]) -> list[CombatMatchup]:
    combat_matchups: list[CombatMatchup] = []
    for attacker in attacking_army:
       for defender in defending_army:
           for phase in (WeaponType.RANGED, WeaponType.MELEE):
               damage = unit_damage(attacker_unit=attacker, target_unit=defender, phase=phase)               
               current_matchup = CombatMatchup(attacker=attacker["ref"]["id"], defender=defender["ref"]["id"], combat_phase=phase, damage=damage)
               combat_matchups.append(current_matchup)
    return combat_matchups