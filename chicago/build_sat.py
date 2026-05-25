#!/usr/bin/env python3
"""Chicago darkness x crime — calibrated VIIRS Black Marble annual radiance."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common_sat_bm

# 2023 falls inside Chicago's crime window (2023-01-01 .. start of current month).
common_sat_bm.build(os.path.dirname(os.path.abspath(__file__)), year=2023,
                    lighting_label="VIIRS annual radiance, 2023")
