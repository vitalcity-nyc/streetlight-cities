#!/usr/bin/env python3
"""Baltimore fetch adapter — ArcGIS Feature Services (Open Baltimore), keyless."""
import sys, os, urllib.parse, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common

# BPD Part 1 crime carries coordinates only through late Dec 2024, so both layers
# are capped to calendar 2023-2024 to keep the crime and 311 windows matched.
WIN_START = "2023-01-01"
WIN_END = "2025-01-01"
ORG = "https://services1.arcgis.com/UWYHeuuJISiGmgXx/arcgis/rest/services"
SR_YEARS = ["311_Customer_Service_Requests_2023", "311_Customer_Service_Requests_2024"]
CRIME_SVC = "Part1_Crime_Beta"


def arcgis(service, where, out_fields):
    """Page an ArcGIS FeatureServer/0 layer, yielding attribute dicts."""
    offset, limit = 0, 2000
    base = f"{ORG}/{service}/FeatureServer/0/query"
    while True:
        params = {"where": where, "outFields": out_fields, "returnGeometry": "false",
                  "resultOffset": offset, "resultRecordCount": limit, "f": "json"}
        j = common.fetch_json(f"{base}?" + urllib.parse.urlencode(params))
        feats = j.get("features", [])
        if not feats:
            break
        for ft in feats:
            yield ft["attributes"]
        if not j.get("exceededTransferLimit") and len(feats) < limit:
            break
        offset += limit
        print(f"    …{offset} {service}", file=sys.stderr)


def epoch_to_iso(ms):
    if ms in (None, ""):
        return ""
    try:
        return datetime.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%dT%H:%M:%S")
    except (TypeError, ValueError, OSError):
        return ""


SR_WHERE = ("(UPPER(SRType) LIKE '%STREET LIGHT%' OR UPPER(SRType) LIKE '%STLIGHT%' "
            "OR UPPER(SRType) LIKE '%ST LIGHT%')")

print("Baltimore: fetching 311 streetlight complaints…", file=sys.stderr)
outages = []
for svc in SR_YEARS:
    for a in arcgis(svc, SR_WHERE, "SRType,CreatedDate,Address,Neighborhood,Latitude,Longitude"):
        lat, lon = common.fnum(a.get("Latitude")), common.fnum(a.get("Longitude"))
        if lat and lon:
            outages.append({"lat": lat, "lon": lon, "date": epoch_to_iso(a.get("CreatedDate")),
                            "addr": a.get("Address"), "area": a.get("Neighborhood")})
print(f"  {len(outages)} complaints with coords", file=sys.stderr)

CRIME_WHERE = ("(Description LIKE '%ASSAULT%' OR Description LIKE '%ROBBERY%' "
               "OR Description='HOMICIDE' OR Description='SHOOTING') "
               "AND (Inside_Outside <> 'I' OR Inside_Outside IS NULL) "  # exclude indoor; keep outdoor + blank
               f"AND CrimeDateTime >= DATE '{WIN_START}' AND CrimeDateTime < DATE '{WIN_END}'")
print("Baltimore: fetching Part 1 crime…", file=sys.stderr)
crimes = []
for a in arcgis(CRIME_SVC, CRIME_WHERE, "CrimeDateTime,Description,Neighborhood,Latitude,Longitude"):
    lat, lon = common.fnum(a.get("Latitude")), common.fnum(a.get("Longitude"))
    if not (lat and lon):
        continue
    iso = epoch_to_iso(a.get("CrimeDateTime"))
    if iso[:10] < WIN_START:
        continue
    hour = int(iso[11:13]) if len(iso) >= 13 else 12
    crimes.append({"lat": lat, "lon": lon, "date": iso, "night": common.is_night(hour),
                   "area": a.get("Neighborhood")})
print(f"  {len(crimes)} street-level violent crimes with coords", file=sys.stderr)

common.build(outages, crimes, city="Baltimore", win_start=WIN_START,
             out_dir=os.path.dirname(os.path.abspath(__file__)),
             bbox=(-76.76, 39.18, -76.50, 39.40))
