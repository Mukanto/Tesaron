# Freeze record: Tesaron v0.3

This record is outside the freeze manifest (PREREG v0.3 §9). It is appended to, never rewritten.

## Freeze (PREREG v0.3 §8, step 7)

| Item | Value |
|---|---|
| Date | 2026-11-23 (manifest written 2026-11-23T16:12:47Z; freeze commit 2026-11-23T19:13:03+03:00) |
| Pre-registration | `prereg/PREREG_v0.3.md`, draft 3, with `SPEC_v0.3.md` |
| Manifest | `prereg/v03/FREEZE_v0.3.json`, 177 files |
| Core hash | `2bfd7ec16225e721e2e4e01d21877da22e77b2528730f03fb2da2b29ab2d67a8` |
| Freeze commit | `5de2da80a2c07c22044b5d7099e122522590bf59` |
| Run machine | `platform.platform()`: `Windows-11-10.0.26300-SP0`; Python `3.14.2 (tags/v3.14.2:df79316, Dec  5 2025, 17:18:21) [MSC v.1944 64 bit (AMD64)]`; NumPy `2.4.1` |
| Gate | Truth_Gate v0.5.1 (kapi-oss `41967f5e6c325dd505c291104ba103d01c32300e`); eight certificates (G1–G7a, T-1) FALSIFIABLE with no flags; `certify all --verify` exit 0 for all eight; `audit/v03/gate/GATE_TOOL.json` with 136 file hashes; T-1 plus-world draws: 402 accepted, 206 skipped as undefined |
| Status lines | PREREG and SPEC_v0.3 line 3 replaced by the frozen lines of §8 step 6 before the manifest was written |
| Unit tests | 591 passed (504 subtests) on the tree to be frozen, with git tests, after the status lines and GATE_TOOL.json were in place |
| Pre-freeze check | `py -m audit.v03.prefreeze_check` (all five checks: gate tool, tracked files and staged blobs, status lines, the six design studies reproduced, v0.2's manifest): `PRE-FREEZE CHECK OK` |
| Manifest check | `py -m audit.v03.freeze verify --coverage --require-readonly`: `FREEZE OK`; `prereg/FREEZE_v0.2.json` still `FREEZE OK` |
| Clone verification | `py -m audit.v03.clone_verify` on the freeze commit: v0.3 and v0.2 manifests `FREEZE OK`, clone HEAD `5de2da80a2c07c22044b5d7099e122522590bf59`, `CLONE VERIFIES`. The clone's files are writable (git does not keep read-only bits); the hashes all match. |
| Blind reviews | two (`prereg/v03/reviews/`): review 1 (0 blocking, 8 major, 8 minor) and the targeted review 2 (14 of 16 repairs fixed, 2 partly; 0 blocking, 3 major, 7 minor), all repaired (PREREG §10). Review 2 judged the draft ready to freeze once its findings were repaired. |
| No pilot | No T-1 or G8 outcome and no new_false value was read, printed or stored on any v0.3 world before the freeze (PREREG §2). |
| Sign-off | The author, Hazar Şimşek, 2026-11-23: "Dondur, push'u bekle" (freeze now; the push waits for a separate approval) |
| Push | see "Push" below |

## Salt (PREREG v0.3 §8, step 8)

Not yet drawn. The salt is drawn by the Independent session only after the freeze commit is on the public repository.

## Push (appended 2026-11-23)

- The author approved the push ("Push et", 2026-11-23). `5de2da8` and `9efa28d` were pushed to
  `https://github.com/Mukanto/Tesaron.git`, branch `main`; `git ls-remote` then showed `main` at
  `9efa28dca7b5aa7636a96242c27f1c1740cc2ee7`, of which the freeze commit is an ancestor.
- The salt was then requested from the Independent session (task `tesaron_v03_salt`), with the freeze commit
  `5de2da80a2c07c22044b5d7099e122522590bf59` and the core hash
  `2bfd7ec16225e721e2e4e01d21877da22e77b2528730f03fb2da2b29ab2d67a8`.

## Salt drawn (appended 2026-11-23)

| Item | Value |
|---|---|
| Salt | `a3cf5b656f5f698654fc16d9f6f70420caae41da3bd622ed4092127f76c5dad3` |
| Drawn by | the Independent session itself (no subagent), task `tesaron_v03_salt`, with `python secrets.token_hex(32)` |
| Drawn at | 2026-11-23T16:16:36Z, after it read the public `main` with `git ls-remote` at 16:16:30Z (`9efa28d…`, which contains the freeze commit) |
| Given to it | the freeze commit `5de2da80…` and the core hash `2bfd7ec1…`, copied exactly into its record |
| Its record | `E:\Independent\tasks\tesaron_v03_salt\SALT_RECORD.json`, read-only, SHA-256 `711603fcb79dd0699f7f6d531afc10ed2ec972f9ab945c8b9274ed70c48c8f03` (checked by the designer) |
| In the repository | `run/v03/SALT.json` |
