from pathlib import Path
import pytest
from tabletop_tactician.reference_data.roster import Army, load_roster

army_a_path = Path(__file__).parent / "fixtures" / "army_a.txt"
army_b_path = Path(__file__).parent / "fixtures" / "army_b.txt"


def _read_roster_text(path) -> str:
    if not path.exists():
        pytest.skip(f"roster fixture '{path.name}' not present — see tests/fixtures/README.md")

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    return text


@pytest.fixture
def army_a() -> Army:
    return load_roster(_read_roster_text(army_a_path))


@pytest.fixture
def army_b() -> Army:
    return load_roster(_read_roster_text(army_b_path))
