# Handoff: street lighting and crime, beyond New York City

This repo is the whole of the attempt to broaden Vital City's New York City lighting-and-crime maps to other cities. It was built May 24-26, 2026 as a draft for review and has not been edited since, apart from a basemap key fix on Sept. 1. Nothing here is linked from anywhere public.

## What exists

Five cities, each with two maps, all on one shared method:

| City | 311 complaints x crime | Satellite darkness x crime |
|---|---|---|
| New York City | `nyc/index.html` | `nyc/satellite.html` |
| Chicago | `chicago/index.html` | `chicago/satellite.html` |
| Philadelphia | `philadelphia/index.html` | `philadelphia/satellite.html` |
| Baltimore | `baltimore/index.html` | `baltimore/satellite.html` |
| Los Angeles | `los-angeles/index.html` | `los-angeles/satellite.html` |

Plus three combined pages at the root:

- `all-cities-311.html` and `all-cities-satellite.html`: one page each with a city tab bar. The satellite one takes a URL hash like `#city=chicago&l=50&c=80` (lighting percentile at or below 50, crime percentile at or above 80).
- `atlas.html`: New York City's real, untouched maps as the main view, with the four comparison cities as live mini maps along the bottom. `?type=311` switches to the 311 view.
- `index.html`: a plain hub linking every per-city map.

Live: https://vitalcity-nyc.github.io/streetlight-cities/

## Where the research is

- `DATA-SOURCES.md` is the plain-language methodology: every dataset, field, filter, window and caveat per city. Read this first.
- The rest of this file records the dead ends and decisions that never made it into the code. The original working session's transcript is gone, so this is the only written record of them.

## Decisions that shaped the method

- **Nighttime crime only, 8 PM to 6 AM.** Josh's call: darkness is a nighttime condition. The New York City originals count all hours. This is the one methodological split between the originals and the new cities.
- **Indoor incidents excluded** wherever the police file has an indoor/outdoor field. Philadelphia is the only city that has none, so its crime layer includes indoor events.
- **Street-level violent crime only**: assault, robbery, homicide, plus battery where a city uses that category. Sex crimes are excluded everywhere.
- **Each map's two layers share one time window.** Windows differ between cities because the data does. Comparisons are within-city percentiles, never absolute counts across cities.
- **New York City's satellite layer was rebuilt** from the same NASA Black Marble source as the other four so the lighting is apples to apples. The original New York City satellite map uses a different raster (a 2022-2024 composite, provenance credited to Shu Wang, brightness scale running much higher). That original is untouched and still live at its own address.

## Dead ends, so nobody repeats them

- **Miami is blocked.** Miami-Dade County publishes 311 streetlight requests (ArcGIS, split by year), but there is no public point-level crime feed for the City of Miami or the county. The police crime map is a LexisNexis vendor viewer with no download, and Florida crime data is mostly aggregated at the state level. At most Miami could get a 311-only outage map.
- **Free NASA GIBS tiles do not work for this.** The first satellite build (`common_sat.py`, kept but unused) sampled the keyless GIBS nighttime tiles. Those are display-stretched images that saturate across dense cities: in Philadelphia 75 to 90 percent of crime hexes pinned at the palette maximum, leaving no usable within-city darkness variation. GIBS also only keeps about six months of nighttime tiles, so historical matching is impossible there anyway.
- **The fix was calibrated radiance** (`common_sat_bm.py`): NASA Black Marble VNP46A4 annual composites, found via the Common Metadata Repository granule search and downloaded from the LAADS archive with a free Earthdata token. Real radiance runs about 2 to 275 nanowatts per square centimeter per steradian and gives clean terciles.
- **Los Angeles 2024 crime is gutted.** LAPD's mid-2024 records-system change left about 17,000 violent incidents in the coordinate-bearing dataset versus roughly 58,000 in each of 2022 and 2023. The newer NIBRS feed has no coordinates at all. That is why Los Angeles uses calendar 2023 for both layers.
- **Baltimore's legacy crime file ends in 2019.** Use `Part1_Crime_Beta`, not `Part1_Crime`. Its object ID field is `ESRI_OID`, and asking ArcGIS to sort by `OBJECTID` fails silently and returns zero rows. Page with `resultOffset` instead.
- **Los Angeles 311 is split by year** (2023, 2024 and 2025 are separate Socrata datasets) and those yearly sets do not show up in the federated Socrata catalog search. The IDs are hardcoded in `los-angeles/build.py`.
- **Philadelphia's feeds have no neighborhood field.** `label_neighborhoods.py` assigns names by point-in-polygon against `philadelphia/neighborhoods.geojson`. Do not fetch the OpenDataPhilly neighborhoods download endpoint blind; one candidate URL turned out to be a 526 MB building-footprints file.

## The one finding worth knowing before you extend this

In every city, dark and high-crime hexes are rare. Violent crime concentrates in the brightest, busiest areas, the commercial cores, and the darkest areas are low-crime. That matches the criminology (crime follows activity) and it is the honest result. The New York City originals show the same pattern.

## How the code fits together

- `common.py`: shared H3 hex binning (resolution 8 for the four comparison cities, 9 for New York City), tercile bivariate classes, top-20 chronic complaint addresses. Writes `hexes.geojson` and `chronic.json`.
- `<city>/build.py`: a fetch adapter per city, each hitting a different open-data platform (Socrata for Chicago and Los Angeles, Carto SQL for Philadelphia, ArcGIS for Baltimore). All keyless. Sets the window and the crime and complaint filters.
- `common_sat_bm.py` and `<city>/build_sat.py`: add the darkness layer to an existing `hexes.geojson`, writing `hexes-sat.geojson` with per-cell lighting and crime percentiles plus the quantile arrays the sliders read.
- `template.html` and `template-sat.html`: the two page templates. Each city's `index.html` and `satellite.html` are copies, parameterized by `config.js` and `config-sat.js` (bounds, center, copy, caveats).
- `label_neighborhoods.py`: pure-Python point-in-polygon labeling, reusable for any city whose feeds lack a neighborhood field.
- `nyc/` has no `build.py`. Its hexes were pulled live from the existing `bivariate-lighting-crime` repo's `hexes.geojson` and only the satellite layer was added.

## Rebuilding

Python 3 with `h3`, `numpy`, `h5py` and `Pillow`. The satellite builds need a free NASA Earthdata download token in `~/.edl_token` (create one at urs.earthdata.nasa.gov). Downloaded Black Marble tiles cache in `/tmp/blackmarble`, which the operating system clears, so the first run per city downloads again.

```bash
cd chicago && python3 build.py && python3 build_sat.py
```

Preview with any static server (the pages fetch their own GeoJSON, so `file://` will not work). Leaflet, the CARTO dark basemap and the Photon geocoder are loaded from CDNs.

## Related New York City tools this grew out of

These are the originals. They were deliberately not modified during this work.

- Lighting-crime map (satellite, Mapbox): https://vitalcity-nyc.github.io/street-lighting-map/
- Bivariate lighting-crime map (311, Leaflet): https://vitalcity-nyc.github.io/bivariate-lighting-crime/
- Lighting evidence browser (the research literature): https://vitalcity-nyc.github.io/street-lighting-crime/
- Lighting design deep-dive: https://vitalcity-nyc.github.io/rubber-meets-road/

## Not done

- The mini-tile gallery inside the New York City originals (the original end vision) was never started, by design, until the concept was judged.
- No city beyond these five was attempted except Miami.
- Data is frozen at May 2026. Re-running the build scripts refreshes it from the live sources.
