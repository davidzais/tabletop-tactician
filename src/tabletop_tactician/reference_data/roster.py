"""Typed boundary for imported army rosters.

`wh40kdc.try_import_roster` hands back deeply-nested raw dicts
(`roster["units"][i]["wargear"][j]["ref"]["id"]`). This module does that
digging exactly ONCE, here, and returns plain dataclasses. Everywhere else in
the codebase works with `army.faction_id`, `unit.id`, `wg.count` — dot access,
autocomplete, and a red squiggle the moment you typo a field.
"""

from dataclasses import dataclass

import wh40kdc


@dataclass
class Wargear:
    id: str          # weapon datasheet id, e.g. "bolt-rifle"  (flattened from ref.id)
    count: int       # how many models are carrying/firing it


@dataclass
class FieldedUnit:
    id: str                    # unit datasheet id, e.g. "intercessor-squad" (from ref.id)
    model_count: int
    wargear: list[Wargear]


@dataclass
class Army:
    faction_id: str            # e.g. "adeptus-astartes" — lives here, at the army level
    units: list[FieldedUnit]


def load_roster(text: str) -> Army:
    """Parse an exported roster (ListForge/NewRecruit JSON text) into an Army.

    Raises ValueError if wh40kdc can't import it.
    """
    res = wh40kdc.try_import_roster(text)
    if not res["ok"]:
        raise ValueError(
            f"Failed to import roster: {res.get('roster', {}).get('diagnostics')}"
        )

    raw = res["roster"]
    units = [
        FieldedUnit(
            id=u["ref"]["id"],
            model_count=u["model_count"],
            wargear=[
                Wargear(id=w["ref"]["id"], count=w["count"])
                for w in u["wargear"]
                if w["ref"]["id"] is not None  # skip weapons wh40kdc couldn't resolve to an id
            ],
        )
        for u in raw["units"]
    ]
    return Army(faction_id=raw["faction_id"], units=units)