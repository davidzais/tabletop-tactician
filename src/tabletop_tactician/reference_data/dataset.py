from functools import cache
from wh40kdc import Dataset, crunch


def unit_raw(unit_id: str) -> dict:
    dataset = get_dataset()
    return dataset.units.get_any(unit_id).raw
   

def weapon_raw(weapon_id: str) -> dict:
    dataset = get_dataset()
    return dataset.weapons.get_any(weapon_id).raw

def get_stage(crunch_result: dict, stage_name: str) -> float:
    """Pull one stage's expected value out of a crunch result by name."""
    return next(s for s in crunch_result["stages"] if s["name"] == stage_name)["expected"]

# --- one weapon's damage stage ---
def weapon_damage(weapon_raw_dict: dict, target_raw_dict: dict, models_firing: int) -> float:
    result = crunch(
        {
            "attacker": {"weapon": weapon_raw_dict, "profileIndex": 0},
            "target": {"unit": target_raw_dict, "profileIndex": 0},
            "modelsFiring": models_firing,
            "buffs": [],
            "context": {},
        }
    )
    return next(s for s in result["stages"] if s["name"] == "damage")["expected"]

# --- a roster unit's total damage in one phase (the roll-up, loadout-driven) ---
def unit_damage(attacker_unit: dict, target_unit: dict, phase: str) -> float:
    """attacker_entry / target_entry are roster units: {ref, model_count, wargear}."""
    target = unit_raw(target_unit["ref"]["id"])
    total = 0.0
    for wg in attacker_unit["wargear"]:
        wr = weapon_raw(wg["ref"]["id"])
        if wr["type"] != phase:  # phase filter, off the weapon's own type
            continue
        total += weapon_damage(wr, target, wg["count"])  # count = models firing THIS weapon
    return total

@cache
def get_dataset() -> Dataset:
    ds = Dataset.embedded()
    return ds