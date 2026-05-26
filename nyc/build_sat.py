#!/usr/bin/env python3
"""New York City darkness x crime — calibrated VIIRS Black Marble annual radiance.

Crime + 311 hexes are NYC's real bivariate-map data (res 9); this adds the SAME
Black Marble VNP46A4 2023 lighting layer used for every other city, so all five
share one identical, documented lighting source.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common_sat_bm

common_sat_bm.build(os.path.dirname(os.path.abspath(__file__)), year=2023,
                    lighting_label="VIIRS annual radiance, 2023")
