# Freeze record: Tesaron v0.2

This record is outside the freeze manifest (PREREG §9). It is appended to, never rewritten.

## Freeze (PREREG §8, step 7)

| Item | Value |
|---|---|
| Date | 2026-11-22 (manifest written 2026-11-22T16:07:07Z; freeze commit 2026-11-22T19:07:21+03:00) |
| Pre-registration | `prereg/PREREG_v0.2.md`, draft 5 |
| Manifest | `prereg/FREEZE_v0.2.json`, 115 files |
| Core hash | `fc0fabd8e2cdc2dc751ba8bf0d25ecc992e0ae044af2a6cdf598e3d26d659ed0` |
| Freeze commit | `8b09a6f3dbc03193c6aa7b7456c89779765bb603` |
| Run machine | `platform.platform()`: `Windows-11-10.0.26300-SP0`; Python `3.14.2 (tags/v3.14.2:df79316, Dec  5 2025, 17:18:21) [MSC v.1944 64 bit (AMD64)]`; NumPy `2.4.1` |
| Gate | Truth_Gate v0.5.1 (kapi-oss `41967f5e6c325dd505c291104ba103d01c32300e`); nine certificates FALSIFIABLE, verify exit 0; `audit/gate/GATE_TOOL.json` with 91 file hashes |
| Pre-freeze check | `py -m audit.prefreeze_check --gate-tool` and `--tracked`: both OK (115 tracked files = 115 frozen files; every file equal to its staged blob) |
| Clone verification | `py -m audit.clone_verify` on the freeze commit: `FREEZE OK`, clone HEAD `8b09a6f3dbc03193c6aa7b7456c89779765bb603`, `CLONE VERIFIES`. The clone's files are writable (git does not keep read-only bits); the hashes all match. |
| Unit tests | 374 tests OK on the frozen tree (with git tests) |
| Blind reviews | three (`prereg/reviews/`); the third found no blocking finding and judged that no further blind review is needed |
| Sign-off | The author, Hazar Şimşek, 2026-11-22: "Dondur, push'u bekle" (freeze now; the push waits for a separate approval) |
| Push | pending the author's approval |

## Salt (PREREG §8, step 8)

Not yet drawn. The salt is drawn by the Independent session only after the freeze commit is on the public repository.

## Push (appended 2026-11-22)

- The author approved the push ("Push edebilirsin", 2026-11-22). `8b09a6f` and `70960f1` were pushed to
  `https://github.com/Mukanto/Tesaron.git`, branch `main`; `git ls-remote` then showed `main` at
  `70960f198c50e440a9321db943ab3de0725b8d8e`.

## Salt drawn (appended 2026-11-22)

| Item | Value |
|---|---|
| Salt | `e892db2a17e0e5105d654606ff5a6ca210f03f3d30b3705952cd697df3916ec8` |
| Drawn by | the Independent session, task `tesaron_v02_salt`, with `python secrets.token_hex(32)` |
| Drawn at | 2026-11-22T16:17:50Z, after it read the public `main` with `git ls-remote` at 16:17:40Z (`70960f1…`) |
| Given to it | the freeze commit `8b09a6f…` and the core hash `fc0fabd8…` (the designer's message misspelled the `main` commit with an extra digit; the session recorded the value the remote printed) |
| Its own record | `E:\Independent\tasks\tesaron_v02_salt\SALT_RECORD.json` (read-only), SHA-256 `277ee9536c575cb05966ff66847bc4d3cb7b362e2ea6956623e9a3da4b3a6a18`; the post-run audit compares `run/SALT.json` with it (PREREG §8, step 12) |
| Run file | `run/SALT.json`, committed in a strict descendant of the freeze commit |
