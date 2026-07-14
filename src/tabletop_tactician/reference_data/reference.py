"""Lookups into the wh40kdc reference data: id -> raw datasheet / weapon dict.

Pure resolution only — "given an id, hand me the 40k stats." No combat math lives
here (that's combat_mechanics/damage.py).
"""

from functools import cache

from wh40kdc import Dataset


def unit_raw(unit_id: str) -> dict:
    dataset = get_dataset()
    return dataset.units.get_any(unit_id).raw


def weapon_raw(weapon_id: str, faction_id: str) -> dict:
    dataset = get_dataset()

    # try to get the weapon from the actual faction, if its not available, fallback to getting the weapon
    # from first available faction. They should have the same profile
    weapon = dataset.weapons.get_in_faction(id=weapon_id, faction_id=faction_id)
    if weapon is None:
        weapon = dataset.weapons.get_any(id=weapon_id)

    return weapon.raw


@cache
def get_dataset() -> Dataset:
    ds = Dataset.embedded()
    return ds