#!/usr/bin/env python3
"""
Assign a neighborhood name to each hex (by centroid point-in-polygon) and rewrite
a city's hexes.geojson + hexes-sat.geojson. For cities whose 311/crime feeds lack
a neighborhood field (e.g. Philadelphia), so tooltips/hotspot cards show real names.

Usage: python3 label_neighborhoods.py <city_dir> <neighborhoods.geojson> <name_prop>
"""
import sys, json, os


def _in_ring(x, y, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _in_polygon(x, y, rings):
    if not _in_ring(x, y, rings[0]):
        return False
    for hole in rings[1:]:
        if _in_ring(x, y, hole):
            return False
    return True


def _contains(x, y, geom):
    t = geom["type"]
    if t == "Polygon":
        return _in_polygon(x, y, geom["coordinates"])
    if t == "MultiPolygon":
        return any(_in_polygon(x, y, poly) for poly in geom["coordinates"])
    return False


def _centroid(ring):
    pts = ring[:-1]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def main(city_dir, nb_path, name_prop):
    nbs = json.load(open(nb_path))["features"]
    # bbox per neighborhood for a cheap pre-filter
    def bbox(geom):
        xs, ys = [], []
        def walk(c):
            if isinstance(c[0], (int, float)):
                xs.append(c[0]); ys.append(c[1])
            else:
                for cc in c:
                    walk(cc)
        walk(geom["coordinates"])
        return min(xs), min(ys), max(xs), max(ys)
    nb_index = [(bbox(f["geometry"]), f["geometry"], f["properties"].get(name_prop)) for f in nbs]

    def lookup(x, y):
        for (bx0, by0, bx1, by1), geom, name in nb_index:
            if bx0 <= x <= bx1 and by0 <= y <= by1 and _contains(x, y, geom):
                return name
        return None

    for fname in ("hexes.geojson", "hexes-sat.geojson"):
        path = os.path.join(city_dir, fname)
        if not os.path.exists(path):
            continue
        fc = json.load(open(path))
        hit = 0
        for f in fc["features"]:
            x, y = _centroid(f["geometry"]["coordinates"][0])
            nm = lookup(x, y)
            if nm:
                f["properties"]["nta"] = nm
                hit += 1
        json.dump(fc, open(path, "w"))
        print(f"  {fname}: labeled {hit}/{len(fc['features'])} hexes", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
