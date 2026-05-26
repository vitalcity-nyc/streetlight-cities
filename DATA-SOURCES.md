# Where the data came from

Plain-language documentation for the multi-city street-lighting and crime maps
(New York City, Chicago, Philadelphia, Baltimore and Los Angeles). Everything
below is open data pulled from public sources. The comparison-city maps are
drafts for review, not published work.

Last built: May 2026.

---

## 1. What each map shows

Every city has two companion maps:

- **311 complaints × crime** — resident-reported streetlight-outage complaints
  (311 service requests) crossed with violent crime.
- **Satellite darkness × crime** — calibrated nighttime-lights satellite radiance
  crossed with violent crime.

Both put the city on a grid of hexagons (about a few blocks each) and, for every
hexagon, count the events that fall inside it. The maps then compare hexagons by
percentile, so "high crime" or "dark" always means high or dark *relative to the
rest of that same city*. You should not read the absolute numbers across cities
as equivalent — only the within-city rankings.

---

## 2. Crime data (the shared layer on both maps)

Each city's own police department, via that city's open-data portal. We keep
street-level violent categories (the violence street lighting most plausibly
affects) and exclude sex crimes.

**Time of day — nighttime only.** Every map here counts only nighttime violent
crime, **8 PM – 6 AM** by the incident timestamp. Darkness is a nighttime
condition, so daytime incidents are excluded on both the 311 maps and the
satellite maps.

**Indoor vs outdoor.** Where the data carries an indoor/outdoor field, incidents
flagged as indoors are excluded so the map reflects street-level events:
**New York City, Chicago, Los Angeles and Baltimore** all exclude indoor crime.
**Philadelphia is the exception** — its police file has no indoor/outdoor field,
so its crime layer includes indoor incidents and is therefore not directly
comparable on that axis.

Counts in the table below are nighttime incidents (8 PM – 6 AM) over each city's
window — the numbers the maps actually use.

| City | Source / portal | Dataset | Categories kept | Window | Night incidents |
|------|-----------------|---------|-----------------|--------|-----------------|
| New York City | NYPD via NYC Open Data | NYPD complaint data | Felony assault, misdemeanor assault, robbery, murder | Jan 2024 – Mar 2026 | 45,368 |
| Chicago | Chicago Police via data.cityofchicago.org | `ijzp-q8t2` | Assault, battery, robbery, homicide | Jan 2023 – Apr 2026 | 38,544 |
| Philadelphia | Philadelphia Police via phl.carto.com | `incidents_part1_part2` | Aggravated assault (firearm and non-firearm), other assaults, robbery (firearm and non-firearm), criminal homicide | Jan 2023 – Apr 2026 | 64,838 |
| Baltimore | Baltimore Police via Open Baltimore (ArcGIS) | `Part1_Crime_Beta` | Assault, robbery, shooting, homicide (outdoor only) | Jan 2023 – Dec 2024 | 12,832 |
| Los Angeles | LAPD via data.lacity.org | `2nrs-mtv8` (Crime Data 2020 to present) | Assault, battery, robbery, homicide (sex crimes excluded) | Calendar 2023 | 10,853 |

Notes:
- **New York City** crime comes from the existing New York City bivariate map's
  prepared data, not re-fetched.
- **Crime locations are approximate.** Most departments snap each incident to a
  block midpoint or nearest intersection for privacy, so a point can sit a
  hexagon away from where it actually happened.

---

## 3. The 311 streetlight-complaint layer

Resident-reported streetlight problems, from each city's 311 / service-request
system.

| City | Dataset | Complaint types kept | Complaints |
|------|---------|----------------------|------------|
| New York City | NYC 311 (Street Light Condition) | Street light out, multiple lights out, dim, missing lamp, damaged fixture | 50,856 |
| Chicago | `v6vf-nfxy` | Street light out, alley light out, viaduct light out | 148,212 |
| Philadelphia | `public_cases_fc` | "Street Light Outage" service request | 33,561 |
| Baltimore | `311_Customer_Service_Requests_2023` and `_2024` | Street light out, knocked-down or missing-pole reports | 31,496 |
| Los Angeles | `4a4x-mna2` (MyLA311 2023) | Single- and multiple-streetlight issues | 32,258 |

The "show chronic complaint spots" toggle marks the addresses with the most
streetlight complaints in each city's window.

> **311 caveat.** Complaint volume reflects who calls 311 as much as actual
> outage rates, so some neighborhoods are under-reported.

---

## 4. The satellite darkness layer (one identical source for all five cities)

- **Source:** NASA Black Marble, product **VNP46A4** — the annual,
  moonlight-corrected nighttime Day/Night Band radiance composite from the
  Visible Infrared Imaging Radiometer Suite (VIIRS), measured in nanowatts per
  square centimeter per steradian.
- **Year used: 2023 for every city**, so all five are directly comparable.
- **How it was obtained:** NASA's Common Metadata Repository (CMR) granule search
  located the tiles covering each city; the files were downloaded from the
  Land, Atmosphere Near real-time Capability for EOS (LAADS) Distributed Active
  Archive Center using a free NASA Earthdata login. The "all-angle snow-free
  composite" band was read, sampled at each hexagon, log-scaled, then ranked
  into percentiles.

> **Resolution caveat.** VIIRS pixels are about 500 metres, and the band
> captures all upward light — signage, lit lots, headlights, stadiums — not
> streetlights alone. A bright hexagon is not necessarily well lit for a
> pedestrian on a side street.

### About New York City's darkness layer specifically

New York City's *original* published satellite map uses a different,
"VIIRS-equivalent" raster spanning 2022–2024 on a square grid, prepared
separately, whose brightness scale runs much higher (up to ~931 nanowatts versus
~240–370 for the Black Marble composite). To make all five cities strictly
comparable, **the New York City darkness layer in this atlas was rebuilt from the
same Black Marble VNP46A4 2023 source as the other cities** — it is not the
original raster. New York's real crime and 311 data are unchanged. The original
New York City map remains live and untouched at its own address.

Because no single year falls inside every city's crime window (Los Angeles is
2023-only; New York is 2024 onward), 2023 lighting is used everywhere. For New
York that is about a year before its crime window — immaterial, since nighttime
lights change very little year to year.

---

## 5. Neighborhood names

Used only for labels in tooltips and the flagged-locations list.

- **New York City:** neighborhood tabulation areas (in the source data).
- **Chicago:** community areas (in the source data).
- **Baltimore:** neighborhood field (in the source data).
- **Los Angeles:** neighborhood-council name (in the source data).
- **Philadelphia:** the source data has no neighborhood field, so each hexagon
  was matched to a Philadelphia neighborhood by point-in-polygon against an
  OpenStreetMap-derived neighborhoods file (the blackmad/neighborhoods
  Philadelphia boundaries).

---

## 6. Supporting services

- **Basemap:** CARTO dark base tiles (built on OpenStreetMap).
- **Address search:** Photon geocoder (komoot, built on OpenStreetMap).
- **Hexagon grid:** Uber's H3 system — resolution 9 (~a block) for New York City,
  resolution 8 (~a few blocks) for the other four.

---

## 7. The most important caveats, by city

- **Los Angeles — crime year.** The coordinate-bearing LAPD dataset
  (`2nrs-mtv8`) covers 2020–2024, but its 2024 is badly undercounted (about
  17,000 violent incidents versus roughly 58,000 in 2023 and 2022) because of a
  mid-2024 records-system change. The map therefore uses calendar **2023**, the
  most recent complete year, for both layers.
- **Baltimore — crime end date.** Baltimore Police Part 1 coordinates run only
  through the end of 2024, so both layers cover **2023–2024**.
- **Philadelphia — no indoor flag.** Unlike the other cities, the Philadelphia
  police file has no indoor/outdoor field, so indoor incidents are not separated
  out.
- **Windows differ between cities** because the available data does. Within any
  single map, the crime and the other layer share the same window.
- **Comparisons are within-city.** Brightness and crime are ranked against each
  city's own distribution; absolute values are not comparable city to city.

---

## 8. Reproducibility

Every map is built by a small script kept in this repository:
`<city>/build.py` fetches the 311 and crime data and bins it; `common_sat_bm.py`
adds the Black Marble darkness layer; `common.py` holds the shared binning and
percentile logic. Re-running a city's scripts rebuilds its data files from the
live open-data sources.
