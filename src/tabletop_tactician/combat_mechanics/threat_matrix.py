from tabletop_tactician.models.profiles import  WeaponType, CombatMatchup
from tabletop_tactician.combat_mechanics.damage import unit_damage
from tabletop_tactician.reference_data.roster import Army, FieldedUnit,  load_roster
from tabletop_tactician.reference_data.reference import wound_pool, merge_leaders_with_units
from collections import Counter, defaultdict
from scipy.optimize import linear_sum_assignment


def build_combat_matchups(attacking_army: Army, defending_army: Army) -> list[CombatMatchup]:   
    
    # this takes the original roster Army and merges leaders into units, and removes them as individual characters from the list:
    # ie carries the painboy attachment into its associated boyz mob
    merged_attacker = merge_leaders_with_units(attacking_army)
    merged_defender = merge_leaders_with_units( defending_army)

    combat_matchups: list[CombatMatchup] = []
    attacker_labels = unique_labels(merged_attacker.units)
    defender_labels = unique_labels(merged_defender.units)
    for (attacker, a_label) in zip(merged_attacker.units, attacker_labels):
       for (defender, d_label) in zip(merged_defender.units, defender_labels):           
           for phase in (WeaponType.RANGED, WeaponType.MELEE):
               damage = unit_damage(attacker_unit=attacker, target_unit=defender, attacker_faction_id=merged_attacker.faction_id, defender_faction_id=merged_defender.faction_id, phase=phase)                               
               current_matchup = CombatMatchup(attacker=a_label, defender=d_label, combat_phase=phase, damage=damage, wound_pool=defender.wounds, defender_points=defender.points)
               combat_matchups.append(current_matchup)
    return combat_matchups


def process_best_phase_matchup(matchups: list[CombatMatchup]):
    best_matchup_by_phase = {}

    for matchup in matchups:    
        key = (matchup.attacker, matchup.defender)
        current_phase_val = () 
        phase_val = () 
        phase_val = best_matchup_by_phase.get(key, None)
        current_phase_val = (matchup.combat_phase,matchup.value_destroyed)
        if phase_val is None:
            best_matchup_by_phase[key] = current_phase_val
        else:            
            best_matchup_by_phase[key] = phase_val if phase_val[1]> current_phase_val[1] else current_phase_val
    
    return best_matchup_by_phase

def build_value_matrix(best_phase_matchups: dict[tuple, tuple], rows: list[str], columns: list[str]):
   return  [[best_phase_matchups[(row, col)][1] for col in columns]  for row in rows]

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

def assign_targets(attacker: Army, defender: Army) -> tuple[dict[str, tuple], list]:

    # build all the combat matchups
    matchups  = build_combat_matchups(attacker, defender)

    #now for each matchu, get the phase ( ranged or melee ) and pick the one with the highest damage
    best_phase_matchup = process_best_phase_matchup( matchups=matchups)

    #these are lists that will shortly be used for lookup
    row_labels = [key[0] for key in best_phase_matchup.keys()]
    column_labels =  [key[1] for key in best_phase_matchup.keys()]

    # makesure to dedup the lists but preserve the order, thats very important
    row_labels = list(dict.fromkeys(row_labels))
    column_labels = list(dict.fromkeys(column_labels))

    
    # flatten the best-phase dict into a numbers-only grid the solver can read: one row per
    # your unit, one column per enemy target (in the deduped label order), each cell the
    # value_destroyed for that pairing. the solver only understands positions, so the names
    # stay behind in row_labels / column_labels to translate its answer back afterwards.
    grid = build_value_matrix(best_phase_matchup, row_labels, column_labels)

    row_ind, col_ind = linear_sum_assignment( grid, maximize=True)
    holder: dict[str, tuple] = {}
    for r, c in zip( row_ind, col_ind):        
        holder[row_labels[r]] = (column_labels[c], 
                                 best_phase_matchup[(row_labels[r], column_labels[c])][0],
                                 grid[r][c])
    
    #this is the list of attackers that have no target
    dropped_units = [item for item in row_labels if item not in holder.keys()]    
    return holder, dropped_units

if __name__ == "__main__":
    from tabletop_tactician.paths import MY_ARMY

    army = load_roster(MY_ARMY.read_text(encoding="utf-8"))
    attacker_labels = unique_labels(army.units)

  