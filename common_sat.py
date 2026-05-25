#!/usr/bin/env python3
"""
Satellite-darkness x crime build.

Reuses a city's existing hexes.geojson (crime already binned to the same H3 grid
and time-windowed) and adds a NIGHTTIME-DARKNESS layer sampled from NASA's VIIRS
Black Marble gap-filled, BRDF-corrected Day/Night Band radiance, served as
grayscale tiles by NASA GIBS (keyless). Writes hexes-sat.geojson in the same
property shape the page template consumes, with the darkness bin in `light_t`
(so the bivariate palette/legend code is shared with the 311 map).

GIBS only retains these tiles for a rolling ~6-month window, so `dates` must be
recent. Multiple dates are averaged to suppress any residual cloud/noise.
"""
import urllib.request, math, io, json, datetime, sys, bisect, collections
from PIL import Image
import numpy as np

GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"
LAYER = "VIIRS_SNPP_GapFilled_BRDF_Corrected_DayNightBand_Radiance"
TMS = "GoogleMapsCompatible_Level8"
Z = 8


def _lonlat_to_px(lon, lat, z):
    n = (2 ** z) * 256
    x = (lon + 180) / 360 * n
    lr = math.radians(lat)
    y = (1 - math.log(math.tan(lr) + 1 / math.cos(lr)) / math.pi) / 2 * n
    return x, y


def _fetch_tile(tx, ty, date):
    # GIBS serves this layer as a paletted (mode "P") PNG whose index ramps
    # monotonically with radiance. Read the RAW INDEX, not RGB luminance —
    # luminance saturates to ~255 across bright urban cores and destroys the
    # intra-city variation we need.
    url = f"{GIBS}/{LAYER}/default/{date}/{TMS}/{Z}/{ty}/{tx}.png"
    req = urllib.request.Request(url, headers={"User-Agent": "streetlight-cities/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        im = Image.open(io.BytesIO(r.read()))
        if im.mode != "P":
            im = im.convert("L")
        return np.asarray(im, dtype=float)


def _mosaic(bbox, dates):
    """bbox=(minlon,minlat,maxlon,maxlat). Returns {(tx,ty): 256x256 luminance}."""
    minx, _ = _lonlat_to_px(bbox[0], bbox[3], Z)
    maxx, _ = _lonlat_to_px(bbox[2], bbox[1], Z)
    _, topy = _lonlat_to_px(bbox[0], bbox[3], Z)
    _, boty = _lonlat_to_px(bbox[2], bbox[1], Z)
    tx0, tx1 = int(minx // 256), int(maxx // 256)
    ty0, ty1 = int(topy // 256), int(boty // 256)
    n_tiles = (tx1 - tx0 + 1) * (ty1 - ty0 + 1)
    if n_tiles > 64:
        raise SystemExit(f"bbox too large ({n_tiles} tiles) — hexes.geojson likely has stray "
                         f"out-of-city points; rebuild the 311 map with a bbox filter first.")
    tiles = {}
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            arrs = []
            for d in dates:
                try:
                    arrs.append(_fetch_tile(tx, ty, d))
                except Exception as e:
                    print(f"    tile {tx},{ty} {d}: {type(e).__name__}", file=sys.stderr)
            if arrs:
                tiles[(tx, ty)] = np.mean(arrs, axis=0)
    print(f"  mosaic: {len(tiles)} tiles across {len(dates)} date(s)", file=sys.stderr)
    return tiles


def _sample(tiles, lon, lat):
    px, py = _lonlat_to_px(lon, lat, Z)
    tx, ty = int(px // 256), int(py // 256)
    arr = tiles.get((tx, ty))
    if arr is None:
        return None
    ix, iy = int(px % 256), int(py % 256)
    x0, x1 = max(0, ix - 1), min(256, ix + 2)
    y0, y1 = max(0, iy - 1), min(256, iy + 2)
    return float(arr[y0:y1, x0:x1].mean())


def _centroid(ring):
    pts = ring[:-1]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def build_sat(city_dir, *, dates, lighting_label):
    src = json.load(open(f"{city_dir}/hexes.geojson"))
    feats = src["features"]
    lons = [c[0] for f in feats for c in f["geometry"]["coordinates"][0]]
    lats = [c[1] for f in feats for c in f["geometry"]["coordinates"][0]]
    bbox = (min(lons), min(lats), max(lons), max(lats))
    tiles = _mosaic(bbox, dates)

    lums = []
    for f in feats:
        lon, lat = _centroid(f["geometry"]["coordinates"][0])
        f["_lum"] = _sample(tiles, lon, lat)
        if f["_lum"] is not None:
            lums.append(f["_lum"])

    # Terciles of brightness; darkest third = dark bin 2.
    s = sorted(lums)
    t33, t67 = s[len(s) // 3], s[(2 * len(s)) // 3]

    def dark_bin(l):
        if l is None:
            return 0
        if l <= t33:
            return 2
        return 1 if l <= t67 else 0

    def dark_top(l):
        # smaller % = darker / more extreme
        if l is None or not s:
            return None
        return max(0, round(100 * bisect.bisect_right(s, l) / len(s)))

    out_feats = []
    class_counts = collections.Counter()
    for f in feats:
        p = f["properties"]
        db = dark_bin(f["_lum"])
        bv = f"{p['crime_t']}-{db}"
        bvn = f"{p['crime_night_t']}-{db}"
        class_counts[bvn] += 1
        out_feats.append({
            "type": "Feature", "geometry": f["geometry"],
            "properties": {
                "light_n": None if f["_lum"] is None else round(f["_lum"]),
                "light_t": db, "light_top": dark_top(f["_lum"]),
                "crime_n": p["crime_n"], "crime_t": p["crime_t"], "crime_top": p["crime_top"], "bv": bv,
                "crime_night_n": p["crime_night_n"], "crime_night_t": p["crime_night_t"],
                "crime_night_top": p["crime_night_top"], "bv_night": bvn,
                "nta": p.get("nta"), "boro": p.get("boro"),
            }})

    meta = dict(src["meta"])
    meta.pop("outages", None)
    meta["generated"] = datetime.date.today().isoformat()
    meta["class_counts"] = dict(class_counts)
    meta["percentile_method"] = ("Brightness is sampled per hex from VIIRS nighttime radiance and "
                                 "split into terciles; the darkest third is flagged as 'dark'")
    meta["lighting"] = {
        "label": lighting_label,
        "dates": dates,
        "tercile_lum": {"dark_below": round(t33, 1), "mid_below": round(t67, 1)},
        "source": "NASA Black Marble VIIRS gap-filled BRDF-corrected DNB radiance, via NASA GIBS",
    }
    json.dump({"type": "FeatureCollection", "meta": meta, "features": out_feats},
              open(f"{city_dir}/hexes-sat.geojson", "w"))
    print(f"  wrote hexes-sat.geojson — {len(out_feats)} hexes "
          f"({class_counts.get('2-2', 0)} dark+high-crime cells)", file=sys.stderr)
    return meta
