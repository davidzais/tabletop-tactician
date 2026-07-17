from dataclasses import dataclass
from enum import StrEnum


class WeaponType(StrEnum):
    RANGED = "ranged"
    MELEE = "melee"

# @dataclass
# class AttackProfile():
#     skill: int # this will represent BS or WS depending on the WeaponType
#     attacks: int
#     strength: int
#     ap: int
#     damage: int  

# class Keyword(StrEnum):
#     INFANTRY = "Infantry"
#     VEHICLE = "Vehicle"
#     CHARACTER = "Character"
#     MONSTER = "Monster"
#     FLY = "Fly"

# @dataclass
# class DefenseProfile():    
#     toughness: int
#     save: int
#     wounds: int
#     invulnerable: int | None = None
    

# @dataclass
# class Weapon:
#     name: str
#     type: WeaponType
#     attack_profile: AttackProfile
#     range: int | None = None
    

# @dataclass
# class Model:
#     name: str
#     movement: int
#     defense_profile: DefenseProfile
#     leadership: int
#     objective_control: int    
#     weapons: list[Weapon]    
    
# @dataclass
# class Ability:
#     name: str
#     description: str

# @dataclass
# class Unit:    
#     name: str
#     faction_keywords: list[Keyword]
#     models: list[Model]                 
#     abilities: list[Ability]  
#     points_cost: int = 0  
   

@dataclass
class CombatMatchup:
    attacker: str 
    defender: str
    combat_phase: WeaponType
    damage: float
    wound_pool: int
    
    @property
    def fraction_destroyed(self) -> float:
        return min(self.damage, self.wound_pool) / self.wound_pool
    
