import pytest
from tabletop_tactician.models.profiles import (
    AttackProfile, DefenseProfile, Weapon, WeaponType, Model, Unit, Keyword,
)
from tabletop_tactician.combat_mechanics.combat import expected_damage, unit_expected_damage


def test_expected_damage():
    attack = AttackProfile(attacks=2, skill=5, strength=5, ap=0, damage=2)
    target = DefenseProfile(toughness=4, save=5, wounds=2, invulnerable=None)
 
    assert expected_damage(attack, target) == pytest.approx(2 * (2/6) * (4/6) * (1 - (2/6)) * 2) # these values are hit_prob * wound_prob * save_fail_prob * attack.damage

    attack = AttackProfile(attacks=2, skill=3, strength=5, ap=-1, damage=2)
    target = DefenseProfile(toughness=4, save=3, wounds=2, invulnerable=None)

    assert expected_damage(attack, target) == pytest.approx(2 * (4/6) * (4/6) * (1 - (3/6)) * 2)

    attack = AttackProfile(attacks=2, skill=3, strength=5, ap=-1, damage=2)
    target = DefenseProfile(toughness=4, save=3, wounds=2, invulnerable=2)

    assert expected_damage(attack, target) == pytest.approx(2 * (4/6) * (4/6) * (1 - (5/6) )* 2)

     
    attack = AttackProfile(attacks=0, skill=5, strength=5, ap=0, damage=2)
    assert expected_damage(attack, target) == 0.0

    two_attacks = AttackProfile(attacks=2, skill=5, strength=5, ap=0, damage=2)
    one_attack = AttackProfile(attacks=1, skill=5, strength=5, ap=0, damage=2)

    # more attacks must do more damage
    assert expected_damage(two_attacks, target) > expected_damage(one_attack, target)


def test_unit_damage_sums_every_weapon_on_every_model():
    target = DefenseProfile(toughness=4, save=3, wounds=2, invulnerable=None)

    bolter = Weapon(
        name="Bolt Rifle", type=WeaponType.RANGED, range=24,
        attack_profile=AttackProfile(skill=3, attacks=2, strength=4, ap=0, damage=1),
    )
    plasma = Weapon(
        name="Plasma", type=WeaponType.RANGED, range=24,
        attack_profile=AttackProfile(skill=3, attacks=1, strength=8, ap=-3, damage=2),
    )
    chainsword= Weapon(name="Chainsowrd", type=WeaponType.MELEE, attack_profile=AttackProfile(skill=3, attacks=4, strength=5, ap=-1, damage=1))

    # model.defense_profile is irrelevant to the roll-up (it scores vs the passed `target`),
    # so any DefenseProfile is fine here.
    m1 = Model(name="Intercessor", movement=6, defense_profile=target,
               leadership=6, objective_control=2, weapons=[bolter, chainsword])
    m2 = Model(name="Sergeant", movement=6, defense_profile=target,
               leadership=6, objective_control=2, weapons=[bolter, plasma])
    unit = Unit(name="Squad", faction_keywords=[Keyword.INFANTRY], models=[m1, m2], abilities=[])

    # oracle: sum of expected_damage over ALL three weapon-instances (bolter, bolter, plasma)
    expected = (
        expected_damage(bolter.attack_profile, target)
        + expected_damage(bolter.attack_profile, target)
        + expected_damage(plasma.attack_profile, target)
       
    )
    assert unit_expected_damage(unit, target, WeaponType.RANGED) == pytest.approx(expected)

    expected_melee =  expected_damage(chainsword.attack_profile, target)
    assert unit_expected_damage(unit, target, WeaponType.MELEE) == pytest.approx(expected_melee)