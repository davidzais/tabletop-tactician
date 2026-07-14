# Test fixtures — army rosters

The combat tests run against real army lists, but the roster JSONs themselves are
**gitignored**: exported lists embed Games Workshop's copyrighted rules text (ability
and weapon descriptions), so they're kept out of the repo.

To run the combat tests locally, drop two roster exports here:

- `army_a.json`
- `army_b.json`

Export them from **[ListForge](https://list-forge.com/)** (the format `try_import_roster`
resolves most reliably — see `NOTES.md`). Any two armies work — the fixture names are
deliberately generic because the fixture-based tests don't care about faction, only that
there's one attacking and one defending list. (The pistol-rule test builds its own unit and
needs no fixture at all.)

If the files are absent, the fixtures **skip** the affected tests rather than failing — so
`pytest` stays green on a fresh clone without them.

*Unofficial; not affiliated with Games Workshop.*