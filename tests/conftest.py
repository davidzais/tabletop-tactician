from pathlib import Path
import pytest
from tabletop_tactician.reference_data.roster import Army, load_roster

marines_path = Path(__file__).parent / "fixtures" / "space_marines.json"
orks_path = Path(__file__).parent / "fixtures" / "orks.json"



def _read_roster_text(path) -> str:
    if not path.exists():
        pytest.skip(f"roster fixture '{path.name}' not present — see tests/fixtures/README.md")
    
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    return text

@pytest.fixture
def space_marines_army() -> Army:    
    return load_roster( _read_roster_text(marines_path))

@pytest.fixture
def orks_army() -> Army:
    return load_roster( _read_roster_text(orks_path))
