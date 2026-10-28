import os
import runpy
from pathlib import Path


os.environ.pop("BLOQUE3_ONLY", None)
os.environ["CAPEX10_BLOQUE3_ONLY"] = "1"
os.environ.pop("CAPEX10_SUBBLOQUE1_ONLY", None)
os.environ["CAPEX10_HIDE_SUBBLOCK_NAV"] = "1"
runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
