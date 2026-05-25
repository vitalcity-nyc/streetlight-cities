#!/usr/bin/env python3
"""Philadelphia darkness x crime — calibrated VIIRS Black Marble annual radiance."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common_sat_bm

# 2023 falls inside Philadelphia's crime window (2023-01-01 .. 2026-04-30).
common_sat_bm.build(os.path.dirname(os.path.abspath(__file__)), year=2023,
                    lighting_label="VIIRS annual radiance, 2023")
