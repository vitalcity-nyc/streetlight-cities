#!/usr/bin/env python3
"""
Satellite-darkness x crime build using CALIBRATED VIIRS radiance.

Source: NASA Black Marble VNP46A4 (annual, moonlight-adjusted nighttime lights),
distributed as HDF5 on LAADS DAAC. Unlike the display tiles in common_sat.py,
this gives true radiance (nW/cm2/sr) with full dynamic range, so intra-city
darkness variation survives. Radiance is log-scaled before binning.

Requires a NASA Earthdata download token saved at ~/.edl_token.

Reuses each city's existing hexes.geojson (crime already binned to the H3 grid
and time-windowed), adds the darkness layer, writes hexes-sat.geojson in the
shape template-sat.html consumes (darkness bin in light_t).
"""
import os, sys, json, math, datetime, collections, bisect, urllib.request, urllib.parse
import numpy as np
import h5py

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
CACHE = "/tmp/blackmarble"
SUBDATASET = "AllAngle_Composite_Snow_Free"   # primary annual radiance field


def _token():
    p = os.path.expanduser("~/.edl_token")
    if not os.path.exists(p):
        raise SystemExit("Missing ~/.edl_token — create a NASA Earthdata token first.")
    return open(p).read().strip()


def _get(url, token=None, dest=None):
    headers = {"User-Agent": "streetlight-cities/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=600) as r:
        data = r.read()
    if dest:
        open(dest, "wb").write(data)
        return dest
    return data


def _granule_urls(bbox, year):
    """Find VNP46A4 annual tiles covering bbox for `year` via CMR (public search)."""
    w, s, e, n = bbox
    q = urllib.parse.urlencode({
        "short_name": "VNP46A4",
        "temporal": f"{year}-01-01T00:00:00Z,{year}-12-31T23:59:59Z",
        "bounding_box": f"{w},{s},{e},{n}", "page_size": 100})
    entries = json.loads(_get(f"{CMR}?{q}").decode())["feed"]["entry"]
    urls = {}
    for g in entries:
        gid = g.get("producer_granule_id", "") or g.get("title", "")
        if f".A{year}001." not in gid:   # keep the requested annual composite only
            continue
        for l in g.get("links", []):
            href = l.get("href", "")
            if href.endswith(".h5") and href.startswith("http"):
                urls[gid] = href
                break
    return list(urls.values())


def _download(url, token):
    os.makedirs(CACHE, exist_ok=True)
    local = f"{CACHE}/{os.path.basename(url)}"
    if os.path.exists(local) and os.path.getsize(local) > 10000:
        return local
    print(f"  downloading {os.path.basename(url)} …", file=sys.stderr)
    return _get(url, token, local)


def _open_grid(path):
    """Return (radiance 2D float array with NaN fill, lon_min, lat_max) for a tile."""
    f = h5py.File(path, "r")
    # find the subdataset wherever it lives in the HDFEOS tree
    found = []
    f.visititems(lambda name, obj: found.append(name) if name.endswith(SUBDATASET) else None)
    if not found:
        raise SystemExit(f"{SUBDATASET} not found in {path}")
    ds = f[found[0]]
    arr = ds[:].astype(float)
    fill = ds.attrs.get("_FillValue")
    scale = ds.attrs.get("scale_factor", 1.0)
    if fill is not None:
        arr[arr == float(np.array(fill).ravel()[0])] = np.nan
    arr *= float(np.array(scale).ravel()[0])
    # tile origin from filename hHHvVV
    base = os.path.basename(path)
    hi = base.index("h");
    h = int(base[hi+1:hi+3]); v = int(base[hi+4:hi+6])
    return arr, h * 10 - 180, 90 - v * 10


def _centroid(ring):
    pts = ring[:-1]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def build(city_dir, *, year, lighting_label):
    token = _token()
    src = json.load(open(f"{city_dir}/hexes.geojson"))
    feats = src["features"]
    lons = [c[0] for f in feats for c in f["geometry"]["coordinates"][0]]
    lats = [c[1] for f in feats for c in f["geometry"]["coordinates"][0]]
    bbox = (min(lons), min(lats), max(lons), max(lats))

    urls = _granule_urls(bbox, year)
    if not urls:
        raise SystemExit(f"CMR found no VNP46A4 tiles for {year} over {bbox}")
    grids = []
    for url in urls:
        p = _download(url, token)
        arr, lon0, lat0 = _open_grid(p)
        rows, cols = arr.shape
        grids.append((arr, lon0, lat0, rows, cols))

    def radiance_at(lon, lat):
        for arr, lon0, lat0, rows, cols in grids:
            if lon0 <= lon < lon0 + 10 and lat0 - 10 < lat <= lat0:
                c = int((lon - lon0) / 10 * cols)
                r = int((lat0 - lat) / 10 * rows)
                win = arr[max(0, r-1):r+2, max(0, c-1):c+2]
                win = win[~np.isnan(win)]
                if win.size:
                    return float(win.mean())
        return None

    rad = []
    for f in feats:
        lon, lat = _centroid(f["geometry"]["coordinates"][0])
        f["_rad"] = radiance_at(lon, lat)
        if f["_rad"] is not None:
            rad.append(f["_rad"])

    # --- percentile model, echoing the NYC satellite tool ---------------------
    # lighting percentile: 0 = darkest, 100 = brightest (radiance, ascending).
    # crime percentile:    0 = lowest,  100 = highest (total violent crime count).
    rad_sorted = sorted(rad)
    crime_sorted = sorted(p_["crime_n"] for p_ in (f["properties"] for f in feats))

    def pctl(sorted_vals, v):
        if v is None or not sorted_vals:
            return None
        return max(0, min(100, round(100 * bisect.bisect_right(sorted_vals, v) / len(sorted_vals))))

    def quantiles(sorted_vals):
        # 101 values: value at each percentile 0..100
        n = len(sorted_vals)
        return [round(sorted_vals[min(n - 1, int(round(p / 100 * (n - 1))))], 1) for p in range(101)]

    out = []
    for f in feats:
        p = f["properties"]
        out.append({"type": "Feature", "geometry": f["geometry"], "properties": {
            "light_n": None if f["_rad"] is None else round(f["_rad"], 1),
            "light_pctl": pctl(rad_sorted, f["_rad"]),
            "crime_n": p["crime_n"],
            "crime_pctl": pctl(crime_sorted, p["crime_n"]),
            "nta": p.get("nta"), "boro": p.get("boro")}})

    meta = dict(src["meta"]); meta.pop("outages", None)
    meta["generated"] = datetime.date.today().isoformat()
    meta.pop("class_counts", None)
    meta["n_cells"] = len(out)
    meta["percentile_method"] = ("Each cell gets a lighting percentile (satellite radiance, 0 = darkest) "
                                 "and a violent-crime percentile (0 = lowest); the sliders flag cells "
                                 "at or below a lighting percentile AND at or above a crime percentile")
    meta["lightingQ"] = quantiles(rad_sorted)
    meta["crimeQ"] = quantiles(crime_sorted)
    meta["lighting"] = {"label": lighting_label, "year": year,
                        "source": "NASA Black Marble VNP46A4 annual radiance (LAADS DAAC)",
                        "units": "nW/cm2/sr"}
    json.dump({"type": "FeatureCollection", "meta": meta, "features": out},
              open(f"{city_dir}/hexes-sat.geojson", "w"))
    print(f"  wrote hexes-sat.geojson — {len(out)} cells; "
          f"radiance min/med/max = {min(rad):.1f}/{rad_sorted[len(rad)//2]:.1f}/{max(rad):.1f}",
          file=sys.stderr)
    return meta
