# Cover note: F3 recomputation for Tesaron v0.2

Your task is in `INSTRUCTIONS_F3.md`. Follow it exactly. This note only says where things are and what the rules of
this folder are.

- **Inputs:** `inputs/`, one `<world_seed>.json` per test world (30 files).
- **Reading list:** `SPEC.md`, `PREREG_v0.2.md` and `OUTPUT_SCHEMA.json`, in this folder.
- **Your output folder:** `out/`. Write your per-world files, `verdict_table.json` and, if needed, `NOTES.md` there.
  Put your own code in `out/code/` (it is not compared).
- **Running code:** only with `C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe` (Python 3.14.2). As
  the instructions say, do not import `tesaron` or `audit` (they are not in this folder anyway).
- **Rules:** read and write only inside this folder. No network, no git, no other agents. Do not edit the inputs.
- You do not get the run's own numbers. A frozen script compares your files with them afterwards.
