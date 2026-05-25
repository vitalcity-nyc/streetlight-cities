#!/usr/bin/env python3
"""Baltimore darkness x crime — calibrated VIIRS Black Marble annual radiance."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common_sat_bm

# 2023 falls inside Baltimore's crime window (2023-01-01 .. 2024-12-29).
common_sat_bm.build(os.path.dirname(os.path.abspath(__file__)), year=2023,
                    lighting_label="VIIRS annual radiance, 2023")
