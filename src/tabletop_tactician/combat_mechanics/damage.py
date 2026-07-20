"""Damage roll-up: how much a weapon / a whole unit deals to a target.

Built on wh40kdc.crunch for the per-weapon math, plus our loadout-level rules
(the shooting Pistol rule). Reference lookups come from reference_data/reference.py.
"""

from wh40kdc import crunch

from tabletop_tactician.reference_data.roster import FieldedUnit
from tabletop_tactician.reference_data.reference import unit_raw, weapon_raw, get_dataset, get_converted_phase



# --- one weapon's damage stage ---
def weapon_damage(weapon_raw_dict: dict, target_raw_dict: dict, defender_faction_id: str, phase: str, models_firing: int) -> float:

    # this conversion is neccessary for the defensive_buffs_for(), we use ranged/melee
    # but internally api uses shooting/fight
    converted_phase = get_converted_phase(phase=phase)
    unit_input = {"unitId": target_raw_dict["id"], "factionId": defender_faction_id}
    phase_context = {"phase": converted_phase}

    dataset = get_dataset()
    result = crunch(

        {
            "attacker": {"weapon": weapon_raw_dict, "profileIndex": 0},
            "target": {"unit": target_raw_dict, "profileIndex": 0},
            "modelsFiring": models_firing,
            "buffs": dataset.defensive_buffs_for(input=unit_input, context=phase_context),
            "context": {},
        }
    )
    return next(s for s in result["stages"] if s["name"] == "after-fnp")["expected"]


# --- a roster unit's total damage in one phase (the roll-up, loadout-driven) ---
def unit_damage(attacker_unit: FieldedUnit, target_unit: FieldedUnit, attacker_faction_id: str, defender_faction_id: str, phase: str) -> float:
    """attacker_unit / target_unit are type FieldedUnit: {id, model_count, wargear}."""
    target = unit_raw(target_unit.id)
    total = 0.0
    if phase == "melee":
        for wg in attacker_unit.wargear:
            wr = weapon_raw(weapon_id=wg.id, faction_id=attacker_faction_id)
            if wr["type"] != phase:  # phase filter, off the weapon's own type
                continue
            total += weapon_damage(weapon_raw_dict=wr, target_raw_dict=target, defender_faction_id=defender_faction_id, phase=phase, models_firing=wg.count)  # count = models firing THIS weapon
        return total
    else:
        pistol_count = 0
        non_pistol_count = 0
        pistol_holder: list[dict] = []
        total_non_pistol_damage_count = 0.0
        total_pistol_damage = 0.0

        # what we're doing here is we are making the assumption, that pistol would be the last resort for
        # a ranged weapon. If the unit has a bolt_rifle or other ranged weapon, you would opt to shoot that
        # over the lowly pistol, cause it does more damage. So we want to count up all the non pistols and pisols
        # pistol - non pistols will determine how many pistols fire, because all non pistols will fire over the pistol.
        for wg in attacker_unit.wargear:
            wr = weapon_raw(weapon_id=wg.id, faction_id=attacker_faction_id)
            if wr["type"] != phase:  # phase filter, off the weapon's own type
                continue

            if is_pistol(weapon=wr):
                pistol_count += wg.count
                # we want to collect these here, because if we just have the count, and not the actual pistol profile, we wont be able
                # to get the sum from weapon damage, which takes the raw weapon profile
                pistol_holder.append((wr, wg.count))
            else:
                non_pistol_count += wg.count
                total_non_pistol_damage_count += weapon_damage(weapon_raw_dict=wr, target_raw_dict=target, defender_faction_id=defender_faction_id, phase=phase, models_firing=wg.count)

        pistols_that_fire = max(0, pistol_count - non_pistol_count)       
        #lets rank the pistols so we can fire the best ones first, if the unit has more than one
        shot_damages = pistol_shot_damage(pistol_holder=pistol_holder, target_raw_dict=target, defender_faction_id=defender_faction_id, phase=phase)
        total_pistol_damage = pistol_damage(shot_damages, pistols_that_fire)       

    return total_non_pistol_damage_count + total_pistol_damage

# spend the pistol allotment on the hardest-hitting pistols first
def pistol_damage(pistols: list[tuple[float, int]], pistols_that_fire: int) -> float:
    """pistols: (per_shot_damage, count) per pistol type, any order.
    Fires the best pistols first, up to pistols_that_fire, and sums the damage."""
    total = 0.0
    remaining = pistols_that_fire
    for per_shot, count in sorted(pistols, reverse=True):   # best pistol first
        if remaining <= 0:
            break
        firing = min(count, remaining)
        total += per_shot * firing
        remaining -= firing
    return total



#since a unit might have Multiple pistol types, we want to fire the one that hits the hardest
def pistol_shot_damage(pistol_holder: list[tuple], target_raw_dict: dict, defender_faction_id: str, phase: str,):
    pistol_weapons = []
    for (wr, count) in pistol_holder:
        per_shot = weapon_damage(weapon_raw_dict=wr, target_raw_dict=target_raw_dict, defender_faction_id=defender_faction_id, phase=phase, models_firing=1)
        pistol_weapons.append( (per_shot, count) )
    
    return pistol_weapons 


def is_pistol(weapon: dict) -> bool:
    return any(kw["keyword_id"] == "pistol" for p in weapon["profiles"] for kw in p.get("keywords", []))