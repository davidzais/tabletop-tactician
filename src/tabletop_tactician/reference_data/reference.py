"""Lookups into the wh40kdc reference data: id -> raw datasheet / weapon dict.

Pure resolution only — "given an id, hand me the 40k stats." No combat math lives
here (that's combat_mechanics/damage.py).
"""

from functools import cache
from wh40kdc import Dataset
from tabletop_tactician.reference_data.roster import Army, FieldedUnit, PhaseBuffs, UnitBuffs
from dataclasses import replace


def get_converted_phase(phase: str) -> str:
    """we define the phases of combat as ranged and melee.
    Some function of the api require these to be "shooting" or "fight"
    This is just a simple utility function to do that conversion

    Args:
        phase (str): the source phase (ranged or melee)

    Returns:
        str: the converted phase (shooting or fight)
    """
    return "shooting" if phase == "ranged" else "fight"


def unit_raw(unit_id: str) -> dict:
    dataset = get_dataset()
    return dataset.units.get_any(unit_id).raw


def weapon_raw(weapon_id: str, faction_id: str) -> dict | None:
    dataset = get_dataset()

    # try to get the weapon from the actual faction, if its not available, fallback to getting the weapon
    # from first available faction. They should have the same profile
    weapon = dataset.weapons.get_in_faction(id=weapon_id, faction_id=faction_id)
    if weapon is None:
        weapon = dataset.weapons.get_any(id=weapon_id)

    return weapon.raw if weapon is not None else None


def get_unsupported_abilities(army: Army, phase: str) -> dict[str, dict[str, str]]:
    """List, per unit, the rules the damage engine could NOT account for.

    This is the "honest about the gaps" feature. crunch only models damage it can
    compute from static stats, so abilities that depend on live game state (e.g.
    "while attached", "while below half strength") or that aren't damage math at all
    (movement, ability grants) get left out. We surface those so the app can tell the
    user "heads up - I didn't factor in X".

    Returns { unit_id: { ability_name: plain-English description } }; units with
    nothing unmodeled are omitted entirely.
    """
    dataset = get_dataset()
    unit_ability_holder: dict[str, dict[str, str]] = {}
    converted_phase = get_converted_phase(phase=phase)
    for unit in army.units:
        # the library keys ability lookups by unit id + faction; phase is "shooting"/"fight"
        unit_input = {"unitId": unit.id, "factionId": army.faction_id}
        phase_context = {"phase": converted_phase, "attackerAttached": unit.leader_attachment is not None}

        # build this unit's {ability_name: description} map of gaps.
        # eligible_abilities -> every ability that could apply this phase (each entry
        #   is {"ability": AbilityView, "source": ...}).
        # describe_buffs(..., "target") -> {"applied", "unsupported", ...}; a non-empty
        #   "unsupported" means the engine couldn't translate part of it = a real gap.
        # ability.describe() -> the plain-English text we show the user.
        ability_holder: dict[str, str] = {}
        for entry in dataset.eligible_abilities(unit_input, converted_phase):
            ability = entry["ability"]
            diagnostics = ability.describe_buffs(entry["source"], phase_context, "target")
            if diagnostics["unsupported"]:
                # these are always attachment abilities, no effect on combat
                if ability.raw["effect"]["type"] == "ability-grant":
                    continue
                ability_holder[ability.name] = ability.describe()

        # skip units that had no gaps at all - they don't belong in the report
        if len(ability_holder) == 0:
            continue
        unit_ability_holder[unit.id] = ability_holder

    return unit_ability_holder


def get_attachement_buffs(army: Army, phase: str, side: str) -> dict[str, str]:
    merged = merge_leaders_with_units(army)  # so squads carry their .leaders and merged names  
    result = {}

    for unit in merged.units:
        if len(unit.leaders) == 0:  # nobody joined this squad -> nothing to credit
            continue

        phase_buffs = unit.buffs.defensive if side == "defensive" else unit.buffs.offensive
        buffs = phase_buffs.shooting if phase == "ranged" else phase_buffs.fight

        leader_buffs = leader_buff_filter(buffs=buffs, leaders=unit.leaders)

        buffs_for_this_unit = {}
        for buff in leader_buffs:
            label = describe_buff(contribution=buff["contribution"], side=side)
            leader_id = buff["source"]["sourceUnitId"]
            pretty = leader_id.replace("-", " ").title()
            buffs_for_this_unit[label] = pretty        

        if buffs_for_this_unit:
            result[unit.name] = buffs_for_this_unit

    return result


#get the description for the buffs so we can pass this up to teh llm
#side is either offensive or defensive. this is needed because they both have a hit-mod
#and wound-mod type, and it has a differnt meaning depending on what side you are viewing it from i.e.
#    from the defender's point of view — "-1 to be hit", "-1 to be wounded". 
#    On the attacker's side the same type means the opposite: +1 to hit, +1 to wound
def describe_buff(contribution: dict[str, object], side: str) -> str:
    # example of what the contribution contains
    # {'type': 'wound-mod', 'value': -1}
    # {'type': 'feel-no-pain', 'threshold': 6}
    # ...   
    buff_type = contribution["type"]
    type_val = buff_type.replace("-", " ").title()

    if "threshold" in contribution:  # noqa: SIM102
        # as of 7/25/26 these are the only ones that im aware of, that may change
        # in the future so guard against it in case there may at some point
        # that isnt a + modifier
        if buff_type in ("feel-no-pain", "invulnerable-save"):
            return f"{type_val} {contribution['threshold']}+"
    elif "value" in contribution:
        val = contribution["value"]
        if buff_type == "hit-mod":
            return f"{val:+d} to be hit" if side == "defensive" else f"{val:+d} to hit"
        elif buff_type == "toughness-mod":
            return f"{val:+d} Toughness"
        elif buff_type == "damage-reduction":
            return f"Damage -{val}"
        elif buff_type == "wound-mod":
            return f"{val:+d} to be wounded" if side == "defensive" else f"{val:+d} to wound"
        elif buff_type == "attacks-mod":
            return f"{val:+d} Attack"
        elif buff_type == "strength-mod":
            return f"{val:+d} Strength"
        elif buff_type == "ap-mod":
            return f"{val:+d} AP"       
    elif buff_type == "extra-keyword":           
        return _format_extra_keyword_helper(contribution=contribution)
    elif "roll" in contribution:
        return _format_reroll_helper(contribution=contribution)
    else:
        return type_val

    return type_val

def _format_reroll_helper(contribution: dict)-> str:
    buff_type = contribution["type"]
    # this will be either of hit or wound
    roll_type = contribution["roll"]
    
    #this will be one of ones/all/failed
    if "subset" in contribution:
        subset = contribution["subset"]        
        if subset == "ones":
            return f"Re-roll {roll_type} rolls of 1"
        if subset == "all":
            return f"Re-roll all {roll_type} rolls"
        if subset == "failed":
            return f"Re-roll failed {roll_type} rolls"
        else:
            return buff_type
    else:
        return buff_type

def _format_extra_keyword_helper(contribution: dict)-> str:
    ref = contribution["keywordRef"]
    name = ref["keyword_id"].replace("-", " ").title()  
    params = ref.get("parameters")

    if not params:                                       # e.g. Devastating Wounds
        return name
    if "value" in params:                                # e.g. Sustained Hits 1
        return f"{name} {params['value']}"
    if "target_keyword" in params:                       # e.g. Anti-Psyker 4+
        return f"Anti-{params['target_keyword']} {params['threshold']}+"
    return name 

def wound_pool(unit: FieldedUnit) -> int:
    profiles = {p["name"]: p["W"] for p in unit_raw(unit.id)["profiles"]}

    num_profiles = len(profiles)
    total_wounds = 0

    # if there is only one profile, its just that profiles Wound value times the number of models
    if num_profiles == 1:
        return unit.model_count * next(iter(profiles.values()))

    # if there is no compositions, there was no group_loadout from building the roster
    if not unit.composition:
        min_wound = get_min_wound(profiles)
        return unit.model_count * min_wound

    for comp in unit.composition:
        total_wounds += comp.count * profiles.get(comp.model, get_min_wound(profiles))

    if total_wounds == 0:
        raise ValueError("wound pool can not be 0")

    return total_wounds


def get_min_wound(profiles: dict[str, int]) -> int:
    return min(profiles.values())


def merge_leaders_with_units(army: Army) -> Army:
    dataset = get_dataset()
    merged_units: list[FieldedUnit] = []
    for unit in army.units:
        unit_input = {"unitId": unit.id, "factionId": army.faction_id, "attachedUnitIds": unit.leaders}

        defensive = PhaseBuffs(
            shooting = dataset.defensive_buffs_for(unit_input, {"phase": "shooting"}),
            fight    = dataset.defensive_buffs_for(unit_input, {"phase": "fight"}),
        )
        
        

        if unit.leader_attachment is not None:
            # this unit joined a squad, so it's no longer a unit of its own
            continue

        if not unit.leaders:
            # nobody joined this unit — pass it through, just filling in its wounds
            merged_units.append(replace(unit, wounds=wound_pool(unit), buffs=UnitBuffs(defensive, offensive=PhaseBuffs())))
            continue

        # someone joined this squad. gather the squad and its leaders into one list —
        # "the pieces of the combined unit" — then every total is a sum over the pieces.
        leaders = [get_unit_by_id(unit_id=leader_id, units=army.units) for leader_id in unit.leaders]
        offensive = PhaseBuffs(
                    shooting = leader_buff_filter(buffs=dataset.buffs_for(input=unit_input, context={"phase": "shooting"}), leaders=unit.leaders),
                    fight    = leader_buff_filter(buffs=dataset.buffs_for(input=unit_input, context={"phase": "fight"}), leaders=unit.leaders),
                )
        parts = [unit] + leaders
        
        # gather every part's weapons and models into two flat lists
        all_wargear = []
        all_composition = []
        for part in parts:
            all_wargear += part.wargear
            all_composition += part.composition
        leader_names = ", ".join([l.name for l in leaders])

        merged_unit = FieldedUnit(
            id=unit.id,
            name=f"{unit.name} with ( {leader_names} )",
            model_count=sum(part.model_count for part in parts),
            wargear=all_wargear,
            points=sum(part.points for part in parts),
            wounds=sum(wound_pool(part) for part in parts),
            composition=all_composition,
            leader_attachment=unit.leader_attachment,
            leaders=unit.leaders,
            buffs=UnitBuffs(defensive, offensive)
        )
        merged_units.append(merged_unit)

    return Army(faction_id=army.faction_id, units=merged_units)


def get_unit_by_id(unit_id: str, units: list[FieldedUnit]) -> FieldedUnit:
    target = [unit for unit in units if unit.id == unit_id]
    return target[0]

def leader_buff_filter( buffs: list[dict[str, Any]], leaders: list[str]):
    # keeps only the buffs whose source is one
    # of the leaders — dropping the squad's own abilities and its weapon keywords (which
    # crunch already handles)
    filtered_buffs: list = []
    for buff in buffs:
        if buff.get("source", {}).get("sourceUnitId") in leaders:
            filtered_buffs.append(buff)

    return filtered_buffs

@cache
def get_dataset() -> Dataset:
    ds = Dataset.embedded()
    return ds
