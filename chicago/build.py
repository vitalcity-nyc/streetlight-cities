#!/usr/bin/env python3
"""Chicago fetch adapter — Socrata (data.cityofchicago.org), keyless."""
import sys, os, urllib.parse, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common

WIN_START = "2023-01-01"
# Both layers end at the start of the current month so crime and outages cover
# an identical window (crime has a few days' reporting lag; this keeps them matched).
WIN_END = datetime.date.today().replace(day=1).isoformat()
RES = "https://data.cityofchicago.org/resource"
CRIME_TYPES = ["ASSAULT", "BATTERY", "ROBBERY", "HOMICIDE"]
STREETLIGHT_SR = ["Street Light Out Complaint", "Alley Light Out Complaint", "Viaduct Light Out Complaint"]
INDOOR = ("APARTMENT","RESIDENCE","HOUSE","HOTEL","MOTEL","SCHOOL","HOSPITAL","STORE","RESTAURANT",
          "BAR ","TAVERN","OFFICE","BANK","CHURCH","FACTORY","WAREHOUSE","AIRPORT","RETAIL","NURSING",
          "DAY CARE","FUNERAL","GOVERNMENT BUILDING","BARBER","MEDICAL","COLLEGE","LIBRARY","MOVIE",
          "BOWLING","CLEANERS","DENTAL","GARAGE","BASEMENT","STAIRWELL","ELEVATOR","VEHICLE")
COMMUNITY_AREAS = {
 1:"Rogers Park",2:"West Ridge",3:"Uptown",4:"Lincoln Square",5:"North Center",6:"Lake View",
 7:"Lincoln Park",8:"Near North Side",9:"Edison Park",10:"Norwood Park",11:"Jefferson Park",
 12:"Forest Glen",13:"North Park",14:"Albany Park",15:"Portage Park",16:"Irving Park",17:"Dunning",
 18:"Montclare",19:"Belmont Cragin",20:"Hermosa",21:"Avondale",22:"Logan Square",23:"Humboldt Park",
 24:"West Town",25:"Austin",26:"West Garfield Park",27:"East Garfield Park",28:"Near West Side",
 29:"North Lawndale",30:"South Lawndale",31:"Lower West Side",32:"Loop",33:"Near South Side",
 34:"Armour Square",35:"Douglas",36:"Oakland",37:"Fuller Park",38:"Grand Boulevard",39:"Kenwood",
 40:"Washington Park",41:"Hyde Park",42:"Woodlawn",43:"South Shore",44:"Chatham",45:"Avalon Park",
 46:"South Chicago",47:"Burnside",48:"Calumet Heights",49:"Roseland",50:"Pullman",51:"South Deering",
 52:"East Side",53:"West Pullman",54:"Riverdale",55:"Hegewisch",56:"Garfield Ridge",57:"Archer Heights",
 58:"Brighton Park",59:"McKinley Park",60:"Bridgeport",61:"New City",62:"West Elsdon",63:"Gage Park",
 64:"Clearing",65:"West Lawn",66:"Chicago Lawn",67:"West Englewood",68:"Englewood",
 69:"Greater Grand Crossing",70:"Ashburn",71:"Auburn Gresham",72:"Beverly",73:"Washington Heights",
 74:"Mount Greenwood",75:"Morgan Park",76:"O'Hare",77:"Edgewater"}


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


def ca_name(v):
    n = common.fnum(v)
    return COMMUNITY_AREAS.get(int(n)) if n else None


print("Chicago: fetching 311 streetlight complaints…", file=sys.stderr)
sr_filter = " OR ".join(f"sr_type='{t}'" for t in STREETLIGHT_SR)
outages = []
for r in socrata("v6vf-nfxy.json", {
        "$select": "latitude,longitude,created_date,street_address,community_area",
        "$where": f"created_date>='{WIN_START}' AND created_date<'{WIN_END}' AND ({sr_filter})"}):
    lat, lon = common.fnum(r.get("latitude")), common.fnum(r.get("longitude"))
    if lat and lon:
        outages.append({"lat": lat, "lon": lon, "date": r.get("created_date"),
                        "addr": r.get("street_address"), "area": ca_name(r.get("community_area"))})
print(f"  {len(outages)} complaints with coords", file=sys.stderr)

print("Chicago: fetching crime…", file=sys.stderr)
ct_filter = " OR ".join(f"primary_type='{t}'" for t in CRIME_TYPES)
crimes = []
for r in socrata("ijzp-q8t2.json", {
        "$select": "latitude,longitude,date,primary_type,location_description,community_area",
        "$where": f"date>='{WIN_START}' AND date<'{WIN_END}' AND ({ct_filter})"}):
    lat, lon = common.fnum(r.get("latitude")), common.fnum(r.get("longitude"))
    if not (lat and lon):
        continue
    if any(k in (r.get("location_description") or "").upper() for k in INDOOR):
        continue
    d = r.get("date") or ""
    hour = int(d[11:13]) if len(d) >= 13 else 12
    crimes.append({"lat": lat, "lon": lon, "date": d, "night": common.is_night(hour),
                   "area": ca_name(r.get("community_area"))})
print(f"  {len(crimes)} street-level violent crimes with coords", file=sys.stderr)

common.build(outages, crimes, city="Chicago", win_start=WIN_START,
             out_dir=os.path.dirname(os.path.abspath(__file__)),
             bbox=(-87.97, 41.60, -87.48, 42.07))
