"""Typed boundary for imported army rosters.

`wh40kdc.try_import_roster` hands back deeply-nested raw dicts
(`roster["units"][i]["wargear"][j]["ref"]["id"]`). This module does that
digging exactly ONCE, here, and returns plain dataclasses. Everywhere else in
the codebase works with `army.faction_id`, `unit.id`, `wg.count` — dot access,
autocomplete, and a red squiggle the moment you typo a field.
"""

from dataclasses import dataclass, field

import wh40kdc


@dataclass
class Wargear:
    id: str          # weapon datasheet id, e.g. "bolt-rifle"  (flattened from ref.id)
    count: int       # how many models are carrying/firing it

@dataclass 
class UnitComposition:
    model: str
    count: int

@dataclass
class FieldedUnit:
    id: str                    # unit datasheet id, e.g. "intercessor-squad" (from ref.id)
    model_count: int   
    wargear: list[Wargear]
    points: int = 0
    wounds: int = 0
    composition: list[UnitComposition] = field(default_factory=list)
    leader_attachment: dict | None = None
    leaders: list = field(default_factory=list)
    


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
            points=u["points"],
            composition=[UnitComposition(g["model_name"], g["count"])
             for g in u.get("loadout_groups") or []],
            leader_attachment=u['leader_attachment'] # this could be empty

        )
        for u in raw["units"]
    ]

    assign_leader_to_units( units)
    return Army(faction_id=raw["faction_id"], units=units)


def assign_leader_to_units(units: list[FieldedUnit]):  
    leader_attachments: list[FieldedUnit] = [ u for u in units if u.leader_attachment is not None]

    for leader in leader_attachments:
        leader_id = leader.id
        target_unit_id = leader.leader_attachment["bodyguard_ref"]["id"]

        #for now if there are multiple units, just grab the first one
        for unit in units:
            if unit.id == target_unit_id:
                unit.leaders.append(leader_id)                        
                break


