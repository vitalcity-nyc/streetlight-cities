#!/usr/bin/env python3
"""Philadelphia fetch adapter — Carto SQL API (phl.carto.com), keyless."""
import sys, os, urllib.parse, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common

WIN_START = "2023-01-01"
# Both layers end at the start of the current month so the windows match exactly.
WIN_END = datetime.date.today().replace(day=1).isoformat()
SQL_URL = "https://phl.carto.com/api/v2/sql"
CRIME_CATS = ["Aggravated Assault Firearm", "Aggravated Assault No Firearm", "Other Assaults",
              "Robbery Firearm", "Robbery No Firearm", "Homicide - Criminal"]


def carto(sql):
    offset, limit = 0, 50000
    while True:
        q = f"{sql} LIMIT {limit} OFFSET {offset}"
        j = common.fetch_json(f"{SQL_URL}?" + urllib.parse.urlencode({"q": q}))
        rows = j.get("rows", [])
        if not rows:
            break
        yield from rows
        if len(rows) < limit:
            break
        offset += limit
        print(f"    …{offset}", file=sys.stderr)


print("Philadelphia: fetching 311 streetlight outages…", file=sys.stderr)
outages = []
for r in carto(f"SELECT requested_datetime, address, lat, lon FROM public_cases_fc "
               f"WHERE service_name='Street Light Outage' AND requested_datetime >= '{WIN_START}' "
               f"AND requested_datetime < '{WIN_END}' AND lat IS NOT NULL ORDER BY cartodb_id"):
    lat, lon = common.fnum(r.get("lat")), common.fnum(r.get("lon"))
    if lat and lon:
        outages.append({"lat": lat, "lon": lon, "date": r.get("requested_datetime"),
                        "addr": r.get("address"), "area": None})
print(f"  {len(outages)} complaints with coords", file=sys.stderr)

print("Philadelphia: fetching crime…", file=sys.stderr)
cats = ",".join("'" + c.replace("'", "''") + "'" for c in CRIME_CATS)
crimes = []
for r in carto(f"SELECT text_general_code, dispatch_date_time, ST_Y(the_geom) AS lat, "
               f"ST_X(the_geom) AS lon FROM incidents_part1_part2 "
               f"WHERE dispatch_date_time >= '{WIN_START}' AND dispatch_date_time < '{WIN_END}' "
               f"AND the_geom IS NOT NULL AND text_general_code IN ({cats}) ORDER BY cartodb_id"):
    lat, lon = common.fnum(r.get("lat")), common.fnum(r.get("lon"))
    if not (lat and lon):
        continue
    d = r.get("dispatch_date_time") or ""
    hour = int(d[11:13]) if len(d) >= 13 else 12
    crimes.append({"lat": lat, "lon": lon, "date": d, "night": common.is_night(hour), "area": None})
print(f"  {len(crimes)} street-level violent crimes with coords", file=sys.stderr)

HERE = os.path.dirname(os.path.abspath(__file__))
common.build(outages, crimes, city="Philadelphia", win_start=WIN_START,
             out_dir=HERE, bbox=(-75.31, 39.84, -74.93, 40.16))

# Philadelphia's 311/crime feeds carry no neighborhood field, so label each hex
# by centroid point-in-polygon against a local neighborhoods file (the satellite
# build then inherits these names from hexes.geojson).
import label_neighborhoods
label_neighborhoods.main(HERE, os.path.join(HERE, "neighborhoods.geojson"), "name")
