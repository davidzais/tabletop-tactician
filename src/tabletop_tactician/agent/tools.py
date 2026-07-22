from tabletop_tactician.reference_data.roster import Army, load_roster
from tabletop_tactician.models.profiles import CombatMatchup
from tabletop_tactician.combat_mechanics.threat_matrix import build_combat_matchups, process_best_phase_matchup, build_value_matrix, assign_targets
from pathlib import Path



def load(path: Path) -> Army:
    return load_roster(text=path.read_text(encoding="utf-8"))

def get_threat_matrix( attacker: Army, defender: Army) -> list[dict]:
    
    matchups: list[CombatMatchup] = build_combat_matchups(attacking_army=attacker, defending_army=defender)       

    header = "attacker,defender,phase,damage,wound_pool,fraction_destroyed,points,value_destroyed\n"
    return header + "\n".join(f"{m.attacker},{m.defender},{m.combat_phase},{round(m.damage, 2)},{m.wound_pool},{round(m.fraction_destroyed, 2)},{m.defender_points},{round(m.value_destroyed, 2)}" for m in matchups)

GET_THREAT_MATRIX_TOOL = {
    "type": "function",
    "function": {
        "name": "get_threat_matrix",
        "description": (
            "Get the matchup grid for one attack direction: for each of the attacker's units "
            "against each of the defender's units, per phase (ranged, melee) — the expected damage, "
            "the target's total wounds (wound_pool), the fraction of the defender unit destroyed "
            "(0.0-1.0, overkill already removed), the target's points cost (points), and "
            "value_destroyed. value_destroyed is the expected enemy POINTS removed "
            "(fraction_destroyed × the target's points cost); it is measured in points, NOT a "
            "percentage, so it can exceed 100. Your offensive target assignment is already computed "
            "from value_destroyed and given to you separately, so use this grid for the supporting "
            "numbers (damage, wounds, fraction) on each pairing and to work out the defensive section — "
            "do not use it to re-pick your offensive targets. Call with attacker='me' to see your "
            "offense, attacker='opponent' to see the threat against you. Call it twice for both directions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "attacker": {
                    "type": "string",
                    "enum": ["me", "opponent"],
                    "description": "Whose units are doing the attacking in this grid.",
                },
            },
            "required": ["attacker"],
        },
    },
}





if __name__ == "__main__":   
    from pprint import pprint 
    ROSTERS = Path(__file__).parent.parent.parent.parent / "rosters" 
    attacker_path = Path( ROSTERS / "orks_armageddon.txt")
    defender_path =  Path( ROSTERS /  "sm_armageddon.txt")

    attacker = load(path=attacker_path)
    defender = load(path=defender_path)        

    holder = assign_targets(attacker=attacker, defender=defender)
        
    pprint(holder)
   

    