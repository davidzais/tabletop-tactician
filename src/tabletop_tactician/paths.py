"""One home for the roster files the `__main__` blocks load.

Every module with a "run it and look" block used to work the folder out for itself and
then name its own pair of armies — so `adviser.py`, `tools.py` and `threat_matrix.py`
were each reporting on a DIFFERENT battle, and which answer you got depended on which
file you happened to run. Worse, each one re-derived the folder by walking up four
parents, so a change to the package layout would quietly break all three at once.

Change the two names below and every entry point follows.

These are development conveniences, not application config — the real app takes rosters
from the user. Nothing outside a `__main__` block should import them.
"""

from pathlib import Path

# src/tabletop_tactician/paths.py -> tabletop_tactician -> src -> the repo root
ROSTERS_DIR = Path(__file__).parent.parent.parent / "rosters"

#: The army the reports are written FOR.
MY_ARMY = ROSTERS_DIR / "orks_armageddon.txt"

#: The army it is up against.
ENEMY_ARMY = ROSTERS_DIR / "sm_armageddon.txt"
