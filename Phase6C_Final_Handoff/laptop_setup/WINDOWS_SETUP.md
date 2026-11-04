# Windows setup (analysis only — no GPU, no datasets required)
1. Install Python 3.11 (python.org), tick "Add to PATH".
2. Unzip `Phase6C_Final_Handoff.zip` anywhere (e.g. `C:\Work\Phase6C_Final_Handoff`).
3. PowerShell:
```
cd C:\Work\Phase6C_Final_Handoff
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r laptop_setup\requirements.txt
python scripts\verify_handoff.py --handoff . --regenerate
```
Expected last line: `VERIFY OK`. The environment used originally is in `provenance/environment.txt` (Python 3.11.9, numpy 2.4.6, pandas 2.3.3, scipy 1.17.1, matplotlib 3.11.2).
If script execution is blocked: `Set-ExecutionPolicy -Scope Process Bypass`.
