#!/usr/bin/env python3
"""Los Angeles darkness x crime — calibrated VIIRS Black Marble annual radiance."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common_sat_bm

# Crime is calendar 2023; the 2023 VIIRS annual composite is an exact match.
common_sat_bm.build(os.path.dirname(os.path.abspath(__file__)), year=2023,
                    lighting_label="VIIRS annual radiance, 2023")
