#!/usr/bin/env python3
"""
Shared build logic for the multi-city 311-lighting x crime bivariate maps.

Each city's build.py fetches its own data (different open-data APIs) and hands
two lists of point dicts to build():

  outage = {"lat": float, "lon": float, "date": "YYYY-MM-DD..", "addr": str|None, "area": str|None}
  crime  = {"lat": float, "lon": float, "date": "YYYY-MM-DD..", "night": bool, "area": str|None}

build() bins them into H3 hexes and writes hexes.geojson + chronic.json in the
exact shape template.html consumes — identical data model to the NYC original.
"""
import json, datetime, collections, bisect, urllib.request, urllib.parse, sys
import h3

H3_RES = 8


def fetch_json(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "streetlight-cities/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def is_night(hour):
    return hour >= 20 or hour < 6


def _terciles(values):
    nz = sorted(v for v in values if v > 0)
    if not nz:
        return 1, 2
    mid = nz[len(nz) // 3]
    high = nz[(2 * len(nz)) // 3]
    if high <= mid:
        high = mid + 1
    return mid, high


def _binof(n, mid, high):
    if n <= 0 or n < mid:
        return 0
    return 1 if n < high else 2


def _top_ranker(values):
    nz = sorted(v for v in values if v > 0)
    n = len(nz)

    def rank(v):
        if v <= 0 or n == 0:
            return None
        return max(0, round(100 * (1 - bisect.bisect_left(nz, v) / n)))

    return rank


def _daterange(rows):
    ds = [r["date"][:10] for r in rows if r.get("date")]
    return (min(ds), max(ds)) if ds else (None, None)


def build(outages, crimes, *, city, win_start, out_dir=".", h3_res=H3_RES, bbox=None):
    """Bin points, classify, and write hexes.geojson + chronic.json into out_dir.

    bbox=(minlon, minlat, maxlon, maxlat) clips out stray points (null-island,
    geocoding errors) that would otherwise create hexes far from the city.
    """
    if bbox:
        w, s, e, n = bbox
        def keep(p):
            return w <= p["lon"] <= e and s <= p["lat"] <= n
        before = len(outages), len(crimes)
        outages = [p for p in outages if keep(p)]
        crimes = [p for p in crimes if keep(p)]
        dropped = (before[0] - len(outages)) + (before[1] - len(crimes))
        if dropped:
            print(f"  dropped {dropped} out-of-bbox points", file=sys.stderr)

    cell = lambda lat, lon: h3.latlng_to_cell(lat, lon, h3_res)

    hexes = collections.defaultdict(lambda: {
        "light_n": 0, "crime_n": 0, "crime_night_n": 0, "area": collections.Counter()})

    for o in outages:
        h = hexes[cell(o["lat"], o["lon"])]
        h["light_n"] += 1
        if o.get("area"):
            h["area"][o["area"]] += 1
    for x in crimes:
        h = hexes[cell(x["lat"], x["lon"])]
        h["crime_n"] += 1
        if x.get("night"):
            h["crime_night_n"] += 1
        if x.get("area"):
            h["area"][x["area"]] += 1

    light_mid, light_high = _terciles([h["light_n"] for h in hexes.values()])
    crime_mid, crime_high = _terciles([h["crime_n"] for h in hexes.values()])
    ncrime_mid, ncrime_high = _terciles([h["crime_night_n"] for h in hexes.values()])
    light_top = _top_ranker([h["light_n"] for h in hexes.values()])
    crime_top = _top_ranker([h["crime_n"] for h in hexes.values()])
    ncrime_top = _top_ranker([h["crime_night_n"] for h in hexes.values()])

    feats = []
    class_counts = collections.Counter()
    for c, h in hexes.items():
        if not (h["light_n"] or h["crime_n"]):
            continue
        ring = [[lng, lat] for lat, lng in h3.cell_to_boundary(c)]
        ring.append(ring[0])
        lt = _binof(h["light_n"], light_mid, light_high)
        ct = _binof(h["crime_n"], crime_mid, crime_high)
        nct = _binof(h["crime_night_n"], ncrime_mid, ncrime_high)
        bv, bv_night = f"{ct}-{lt}", f"{nct}-{lt}"
        class_counts[bv_night] += 1
        area = h["area"].most_common(1)[0][0] if h["area"] else None
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "light_n": h["light_n"], "light_t": lt, "light_top": light_top(h["light_n"]),
                "crime_n": h["crime_n"], "crime_t": ct, "crime_top": crime_top(h["crime_n"]), "bv": bv,
                "crime_night_n": h["crime_night_n"], "crime_night_t": nct,
                "crime_night_top": ncrime_top(h["crime_night_n"]), "bv_night": bv_night,
                "nta": area, "boro": city,
            }})

    c_first, c_last = _daterange(crimes)
    o_first, o_last = _daterange(outages)
    meta = {
        "h3_res": h3_res,
        "percentile_method": "Each layer is split into terciles (low / mid / high) over the "
                             "distribution of hexes that have at least one event",
        "generated": datetime.date.today().isoformat(),
        "class_counts": dict(class_counts),
        "crime": {
            "first_date": c_first, "last_date": c_last,
            "total_points": len(crimes),
            "night_total_points": sum(1 for x in crimes if x.get("night")),
            "cuts": {"mid": crime_mid, "high": crime_high},
            "night_cuts": {"mid": ncrime_mid, "high": ncrime_high},
        },
        "outages": {
            "first_date": o_first, "last_date": o_last,
            "total_points": len(outages),
            "cuts": {"mid": light_mid, "high": light_high},
        },
    }
    with open(f"{out_dir}/hexes.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "meta": meta, "features": feats}, f)
    print(f"  wrote hexes.geojson — {len(feats)} hexes "
          f"({class_counts.get('2-2', 0)} story cells)", file=sys.stderr)

    # chronic: top 20 streetlight complaint addresses
    addr_counts = collections.Counter()
    addr_pt = {}
    for o in outages:
        a = (o.get("addr") or "").strip()
        if not a:
            continue
        key = a.upper()
        addr_counts[key] += 1
        addr_pt.setdefault(key, (o["lat"], o["lon"], o.get("area")))
    spots = []
    for a, n in addr_counts.most_common(20):
        lat, lon, area = addr_pt[a]
        spots.append({"lat": lat, "lng": lon, "addr": a.title(), "count": n,
                      "borough": area or city})
    with open(f"{out_dir}/chronic.json", "w") as f:
        json.dump({"spots": spots, "since": win_start}, f)
    print(f"  wrote chronic.json — top {len(spots)} spots", file=sys.stderr)
    return meta
