import wh40kdc
from pathlib import Path
import pytest

marines = Path(__file__).parent / "fixtures" / "space_marines.json"
orks = Path(__file__).parent / "fixtures" / "orks.json"

def load_roster(path: Path)-> list[dict]:
    # Roster fixtures are gitignored (they embed GW's rules text). If they're not
    # present, skip rather than error — see tests/fixtures/README.md.
    if not path.exists():
        pytest.skip(f"roster fixture '{path.name}' not present — see tests/fixtures/README.md")

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

        res = wh40kdc.try_import_roster( text)

        if not res["ok"]:
            raise ValueError(f"Failed to import roster {path}: {res.get('roster', {}).get('diagnostics')}")


        roster: list[dict] = res["roster"]["units"]
    
    return roster

@pytest.fixture
def space_marines_army() -> list[dict]:
    return load_roster( marines)

@pytest.fixture
def orks_army() -> list[dict]:
    return load_roster( orks)
