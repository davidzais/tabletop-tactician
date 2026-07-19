from tabletop_tactician.models.profiles import  WeaponType, CombatMatchup
from tabletop_tactician.combat_mechanics.damage import unit_damage
from tabletop_tactician.reference_data.roster import Army, FieldedUnit,  load_roster
from tabletop_tactician.reference_data.reference import wound_pool
from collections import Counter, defaultdict

def build_combat_matchups(attacking_army: Army, defending_army: Army) -> list[CombatMatchup]:   
    combat_matchups: list[CombatMatchup] = []
    attacker_labels = unique_labels(attacking_army.units)
    defender_labels = unique_labels(defending_army.units)
    for (attacker, a_label) in zip(attacking_army.units, attacker_labels):
       for (defender, d_label) in zip(defending_army.units, defender_labels):           
           for phase in (WeaponType.RANGED, WeaponType.MELEE):
               damage = unit_damage(attacker_unit=attacker, target_unit=defender, attacker_faction_id=attacking_army.faction_id, defender_faction_id=defending_army.faction_id, phase=phase)                               
               current_matchup = CombatMatchup(attacker=a_label, defender=d_label, combat_phase=phase, damage=damage, wound_pool=wound_pool(defender))
               combat_matchups.append(current_matchup)
    return combat_matchups

#this is to handle multiple units with the same name, because they will all be combined into one unit
#since they all have the same name, so we are creating labels to differentiate them
def unique_labels(units: list[FieldedUnit]) -> list[str]:
    seen_units = defaultdict(int)
    counts =  Counter( u.id for u in units )
    
    labels = []
    for unit in units:        
        if counts[unit.id] > 1:
            seen_units[unit.id] += 1            
            labels.append(f"{unit.id} #{seen_units[unit.id]}")
        else:
            labels.append(unit.id)
    return labels



if __name__ == "__main__":
    from pathlib import Path
    ROSTERS = Path(__file__).parent.parent.parent.parent / "rosters" 
    FILE = "orks_1000_gw.txt"
    text = (ROSTERS / FILE).read_text(encoding="utf-8")
    army = load_roster(text)
    attacker_labels = unique_labels(army.units)

    print(attacker_labels)