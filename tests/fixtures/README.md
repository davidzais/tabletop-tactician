# Test fixtures — army rosters

The combat tests run against real army lists, but the roster JSONs themselves are
**gitignored**: exported lists embed Games Workshop's copyrighted rules text (ability
and weapon descriptions), so they're kept out of the repo.

To run the combat tests locally, drop two roster exports here:

- `space_marines.json`
- `orks.json`

Export them from **[ListForge](https://list-forge.com/)** (the format `try_import_roster`
resolves most reliably — see `NOTES.md`). Any two armies work; the tests just need one
attacking and one defending list.

If the files are absent, the fixtures **skip** the affected tests rather than failing — so
`pytest` stays green on a fresh clone without them.

*Unofficial; not affiliated with Games Workshop.*