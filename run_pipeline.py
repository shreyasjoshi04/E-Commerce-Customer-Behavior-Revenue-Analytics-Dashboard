"""Runs the full pipeline: raw data -> cleaning -> EDA/RFM outputs.
Usage:  python scripts/run_pipeline.py
(The PostgreSQL step is separate: python scripts/04_load_to_postgres.py)"""
import runpy
from pathlib import Path

here = Path(__file__).parent
for script in ["01_generate_raw_data.py", "02_data_cleaning.py", "03_eda_rfm_analysis.py"]:
    print(f"\n>>> Running {script}")
    runpy.run_path(str(here / script), run_name="__main__")
print("\nPipeline complete. Outputs: data/processed/ and images/")
