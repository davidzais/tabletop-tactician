from dataclasses import dataclass
from enum import StrEnum


class WeaponType(StrEnum):
    RANGED = "ranged"
    MELEE = "melee"


@dataclass
class CombatMatchup:
    attacker: str
    defender: str
    combat_phase: WeaponType
    damage: float
    wound_pool: int
    defender_points: float

    @property
    def fraction_destroyed(self) -> float:
        return min(self.damage, self.wound_pool) / self.wound_pool

    @property
    def value_destroyed(self) -> float:
        # how many enemy points you expect to remove: the slice you destroy, times what it's worth
        return self.fraction_destroyed * self.defender_points
