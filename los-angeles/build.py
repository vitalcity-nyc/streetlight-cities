#!/usr/bin/env python3
"""Los Angeles fetch adapter — Socrata (data.lacity.org), keyless.

311 streetlight requests live in per-year MyLA311 datasets; the yearly resource
IDs are discovered from the Socrata catalog so the build doesn't go stale.
Crime is the 'Crime Data from 2020 to Present' set (2nrs-mtv8), which carries
coordinates but is frozen at 2024-12-30 — the newer NIBRS feed has no lat/lon.
"""
import sys, os, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common

# LA crime carries coordinates only in the legacy 2020-2024 set, and 2024 in that
# set is badly undercounted (LAPD's 2024 records-system transition: ~17k violent
# incidents vs ~58k in 2023). So this map uses calendar 2023 — the most recent
# COMPLETE year — for both layers (the 2023 MyLA311 file + 2023 crime).
WIN_START = "2023-01-01"
WIN_END = "2024-01-01"
RES = "https://data.lacity.org/resource"
CRIME_ID = "2nrs-mtv8"
SR_YEAR = "4a4x-mna2"  # MyLA311 Service Request Data 2023
SR_TYPES = ["Single Streetlight Issue", "Multiple Streetlight Issue"]
INDOOR = ("DWELLING","APARTMENT","CONDOMINIUM","RESIDENCE","ROOM","GARAGE","STORE","MARKET",
          "MART","RESTAURANT","BAR","NIGHT CLUB","HOTEL","MOTEL","SCHOOL","HOSPITAL","OFFICE",
          "BANK","CHURCH","CLINIC","BUSINESS","MALL","THEATRE","THEATER","SHOP","DEPT",
          "FACILITY","CENTER","STORAGE","WAREHOUSE","BUILDING","ROOMING")


def socrata(path, params):
    offset, limit = 0, 50000
    while True:
        q = dict(params); q["$limit"] = limit; q["$offset"] = offset
        batch = common.fetch_json(f"{RES}/{path}?" + urllib.parse.urlencode(q))
        if not batch:
            break
        yield from batch
        if len(batch) < limit:
            break
        offset += limit
        print(f"    …{offset} {path}", file=sys.stderr)


print("Los Angeles: fetching 311 streetlight requests (calendar 2023)…", file=sys.stderr)
sr_filter = " OR ".join(f"requesttype='{t}'" for t in SR_TYPES)
outages = []
for r in socrata(f"{SR_YEAR}.json", {
        "$select": "createddate,requesttype,address,latitude,longitude,ncname",
        "$where": f"({sr_filter}) AND createddate>='{WIN_START}T00:00:00'"}):
    lat, lon = common.fnum(r.get("latitude")), common.fnum(r.get("longitude"))
    if lat and lon:
        outages.append({"lat": lat, "lon": lon, "date": r.get("createddate"),
                        "addr": r.get("address"), "area": r.get("ncname")})
print(f"  {len(outages)} complaints with coords", file=sys.stderr)

print("Los Angeles: fetching crime…", file=sys.stderr)
crimes = []
for r in socrata(f"{CRIME_ID}.json", {
        "$select": "crm_cd_desc,date_occ,time_occ,lat,lon,area_name,premis_desc",
        "$where": (f"lat!=0 AND date_occ>='{WIN_START}T00:00:00' AND date_occ<'{WIN_END}T00:00:00' AND "
                   "(upper(crm_cd_desc) like '%ASSAULT%' OR upper(crm_cd_desc) like '%ROBBERY%' "
                   "OR upper(crm_cd_desc) like '%HOMICIDE%' OR upper(crm_cd_desc) like '%BATTERY%') "
                   "AND upper(crm_cd_desc) not like '%SEXUAL%'")}):
    lat, lon = common.fnum(r.get("lat")), common.fnum(r.get("lon"))
    if not (lat and lon):
        continue
    if any(k in (r.get("premis_desc") or "").upper() for k in INDOOR):
        continue
    t = (r.get("time_occ") or "").strip()
    hour = int(t) // 100 if t.isdigit() else 12
    crimes.append({"lat": lat, "lon": lon, "date": r.get("date_occ"),
                   "night": common.is_night(hour), "area": r.get("area_name")})
print(f"  {len(crimes)} street-level violent crimes with coords", file=sys.stderr)

common.build(outages, crimes, city="Los Angeles", win_start=WIN_START,
             out_dir=os.path.dirname(os.path.abspath(__file__)),
             bbox=(-118.69, 33.68, -118.13, 34.36))
