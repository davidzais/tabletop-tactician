from tabletop_tactician.models.profiles import AttackProfile, DefenseProfile, Unit, Model, WeaponType

MAX_DIE_ROLL: int =  6

def expected_damage(attack: AttackProfile, target : DefenseProfile) -> float:
    expected_hit = success_probability(attack.skill) * attack.attacks
    wound_prob = success_probability( get_wound_on(strength=attack.strength, toughness=target.toughness))
    save_fail_prob = save_fail_probability( attack=attack, target=target)  
   
    return expected_hit * wound_prob * save_fail_prob * attack.damage


def success_probability(attribute: int) -> float:
    return (7 - attribute) / MAX_DIE_ROLL

def save_fail_probability(attack: AttackProfile, target : DefenseProfile) -> float:
    best_save = target.save - attack.ap
    if target.invulnerable is not None:
        best_save = min(target.save - attack.ap, target.invulnerable)  

    # id this is the case there can be no save
    if best_save > 6:
        return 1.0
    else:
        return 1 - success_probability(best_save)


def get_wound_on( strength: int, toughness: int) -> int:
    if 2 * strength <= toughness:
        return 6
    elif strength >= 2 * toughness:
        return 2
    elif strength > toughness:
        return 3
    elif strength == toughness:
        return 4
    else: 
        return 5
    

def unit_expected_damage(attacker: Unit, target: DefenseProfile, weapon_type: WeaponType) -> float:
    unit_damage = 0.0
    for model in attacker.models:
        for weapon in model.weapons:
            if weapon.type == weapon_type:                
                unit_damage += expected_damage(weapon.attack_profile, target=target)

    return unit_damage
    


    
