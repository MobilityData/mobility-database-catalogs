"""Synthetic warehouse inputs and context caches for the end-to-end test.

Everything is made up and deterministic (fixed random seed), so the same files
are produced on every machine. The stops are laid out to exercise every branch
of the analysis: source cleaning (agency aliases, the regional feed, precursor
feeds, rail-only stops, exact cross-feed duplicates), pair scoring (distance
bands, names, direction and platform conflicts, 150-300 ft rescue), grouping,
physical locations, recommendations, >25-ft issues, unresolved locations,
two-agency BoardingSide recommendations, and road distance / FarthestRoad /
TieBreakRec.

Served shapes and road centerlines are written as caches, so the test never
contacts BigQuery or the Caltrans road service.
"""
import csv, json, math, os, random, sys
from pathlib import Path

STAMP = "20260916_101500"
rng = random.Random(611)
FT_LAT = 1/364000.0
def ft_lon(lat): return 1/(364000.0*math.cos(math.radians(lat)))
def hav_ft(a, b):
    R = 20925721.784777
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*R*math.asin(math.sqrt(h))

AG = {  # code: (analysis_name raw, feed_name, feed_key, route_types, regional_feed_type)
 "MET": ("Los Angeles County Metropolitan Transportation Authority", "LA Metro Bus Schedule", "fk_met", "3", ""),
 "OCT": ("Orange County Transportation Authority", "OCTA Schedule", "fk_oct", "3", ""),
 "LBT": ("Long Beach Transit", "Long Beach Transit Schedule", "fk_lbt", "3", ""),
 "ACT": ("AC Transit", "AC Transit Schedule", "fk_act", "3", ""),             # alias-normalized
 "B511": ("Bay Area 511", "Bay Area 511 Regional Schedule", "fk_511", "3", ""), # excluded
 "FHP": ("Foothill Transit", "Foothill Precursor Schedule", "fk_fhp", "3", "Regional Precursor Feed"),
 "FHT": ("Foothill Transit", "Foothill Transit Schedule", "fk_fht", "3", "Operator Feed"),
 "RAIL": ("Metro Rail", "Metro Rail Schedule", "fk_rail", "1", ""),
 "LRT": ("Metro Light Rail", "Metro Light Rail Schedule", "fk_lrt", "0", ""),      # rail-only (route_type 0)
 "CRR": ("Metrolink", "Metrolink Schedule", "fk_crr", "2", ""),                      # rail-only (route_type 2)
 "CMO": ("Commute.org", "Commute.org Schedules", "fk_cmo", "3", ""),          # alias
 "CMR": ("Commute Raw Feed", "Commute Raw Feed", "fk_cmr", "3", ""),          # fallback label (analysis==feed)
}
STREETS = ["Main", "Pioneer", "Harbor", "Beach", "Lincoln", "Grand", "Broadway", "Olive", "Spring", "Vermont",
           "Western", "Imperial", "Florence", "Central", "Atlantic", "Cherry", "Orange", "Euclid", "Brookhurst", "Magnolia"]
CROSS = ["1st", "2nd", "3rd", "4th", "5th", "South", "Ocean", "Anaheim", "Willow", "Carson", "Del Amo", "Artesia"]

stops = []   # dicts
seq = [0]
def add_stop(ag, cluster, lat, lon, name, desc="", platform="", parent="", loc_type="0", stop_id=None, side=None, routes=None):
    seq[0] += 1
    a = AG[ag]
    sid = stop_id or f"{ag[:2]}{1000+seq[0]}"
    s = dict(code=ag, cluster=cluster, stop_key=f"STK{seq[0]:05d}", analysis_name=a[0], feed_name=a[1], feed_key=a[2],
             _gtfs_key=f"G{seq[0]:05d}", stop_id=sid, stop_name=name, stop_code=str(5000+seq[0]), stop_lat=f"{lat:.7f}",
             stop_lon=f"{lon:.7f}", stop_desc=desc, tts_stop_name="", parent_station=parent, location_type=loc_type,
             platform_code=platform, route_types=a[3], regional_feed_type=a[4], side=side, routes=routes or [])
    stops.append(s); return s

def at(lat, lon, dn_ft, de_ft): return lat + dn_ft*FT_LAT, lon + de_ft*ft_lon(lat)

clusters = []
kinds = ["agree3", "issue3", "two_far", "two_near", "conflict_dir", "rescue", "agree2", "issue4", "two_far", "two_near",
         "platform", "nearfar", "two_far", "agree3", "issue3"]
for ci in range(60):
    kind = kinds[ci % len(kinds)]
    clat = 33.70 + (ci // 10) * 0.02; clon = -118.30 + (ci % 10) * 0.02
    st, cr = STREETS[ci % len(STREETS)], CROSS[ci % len(CROSS)]
    clusters.append((ci, kind, clat, clon, st, cr))
    # east-west street centerline at clat; north side = +dn. Westbound travel (270) -> right side is north.
    nameA = f"{st} St & {cr} Ave"; nameB = f"{st.upper()} ST / {cr.upper()} AVE"; nameC = f"{st} & {cr}"
    j = lambda: rng.uniform(-3, 3)
    if kind in ("agree3", "agree2"):
        ags = ["MET", "OCT", "LBT"] if kind == "agree3" else ["MET", "ACT"]
        for k, ag in enumerate(ags):
            add_stop(ag, ci, *at(clat, clon, 35 + j(), 20 + 6*k + j()), [nameA, nameB, nameC][k % 3], side="N", routes=["WB"])
        add_stop("OCT", ci, *at(clat, clon, -35, -25), nameA + " EB", side="S", routes=["EB"])
    elif kind in ("issue3", "issue4"):
        ags = ["MET", "OCT", "LBT"] + (["FHT"] if kind == "issue4" else [])
        for k, ag in enumerate(ags[:-1]):
            add_stop(ag, ci, *at(clat, clon, 34 + j(), 30 + 4*k + j()), [nameA, nameB, nameC][k % 3], side="N", routes=["WB"])
        off = rng.choice([45, 70, 95, 130])
        add_stop(ags[-1], ci, *at(clat, clon, 36, 30 + off), nameA, side="N", routes=["WB"])
    elif kind == "two_far":
        d = rng.choice([32, 45, 58, 80])
        add_stop("MET", ci, *at(clat, clon, 33, 10), nameA, side="N", routes=["WB"])
        # second agency: same name, same-direction route, but on the wrong (south) side -> UNLIKELY
        add_stop("OCT", ci, *at(clat, clon, -33 if ci % 2 == 0 else 33, 10 + d), nameB, side="S" if ci % 2 == 0 else "N", routes=["WB"])
    elif kind == "two_near":
        add_stop("MET", ci, *at(clat, clon, 30, 0), nameA, side="N", routes=["WB"])
        t = add_stop("LBT", ci, *at(clat, clon, 30 + rng.uniform(4, 18), rng.uniform(-8, 8)), nameC, side="N" if ci % 3 else "S", routes=["WB"] if ci % 4 else ["WB", "EB"])
        if ci % 3 == 0: t["shape_offset_ft"] = 80.0   # this feed's shape is drawn north of the stop -> stop on left of WB travel
    elif kind == "conflict_dir":
        add_stop("MET", ci, *at(clat, clon, 30, 0), nameA + " NB", side="N", routes=["WB"])
        add_stop("OCT", ci, *at(clat, clon, 32, 12), nameA + " SB", side="N", routes=["EB"])
    elif kind == "rescue":
        add_stop("MET", ci, *at(clat, clon, 30, 0), nameA, side="N", routes=["WB"])
        add_stop("LBT", ci, *at(clat, clon, 30, 210), nameA, side="N", routes=["WB"])
    elif kind == "platform":
        add_stop("MET", ci, *at(clat, clon, 30, 0), nameA + " Bay 1", platform="1", side="N", routes=["WB"])
        add_stop("OCT", ci, *at(clat, clon, 30, 8), nameA + " Bay 2", platform="2", side="N", routes=["WB"])
        add_stop("LBT", ci, *at(clat, clon, 31, 4), nameA, platform="1", side="N", routes=["WB"])
    elif kind == "nearfar":
        add_stop("MET", ci, *at(clat, clon, 30, -20), nameA + " Near Side", side="N", routes=["WB"])
        add_stop("OCT", ci, *at(clat, clon, 30, 25), nameA + " Far Side", side="N", routes=["WB"])

# South / Pioneer validation pair (~51.84 ft)
slat, slon = 33.86, -117.99
m = add_stop("MET", 900, *at(slat, slon, 30, 0), "Pioneer / South", stop_id="4389", side="N", routes=["WB"])
o = add_stop("OCT", 900, *at(slat, slon, 30, 51.84), "PIONEER-SOUTH", stop_id="0732", side="N", routes=["WB"])
clusters.append((900, "south_pioneer", slat, slon, "South", "Pioneer"))

# Source-cleaning cases (cluster 950+)
c = 950; clat, clon = 34.40, -118.60; clusters.append((c, "cleaning", clat, clon, "Clean", "Test"))
act = add_stop("ACT", c, *at(clat, clon, 30, 0), "Telegraph Ave & 40th St", side="N", routes=["WB"])
b511 = add_stop("B511", c, *at(clat, clon, 30, 2), "Telegraph Ave & 40th St", side="N", routes=["WB"])
fhp = add_stop("FHP", c, *at(clat, clon, 30, 6), "Telegraph Ave & 40th", side="N", routes=["WB"])
fht = add_stop("FHT", c, *at(clat, clon, 31, 5), "Telegraph & 40th", side="N", routes=["WB"])
rail = add_stop("RAIL", c, *at(clat, clon, 0, 0), "40th Street Station", loc_type="1", side="N", routes=["WB"])
lrt = add_stop("LRT", c, *at(clat, clon, -20, 40), "40th Street Light Rail Platform", side="S", routes=["EB"])
crr = add_stop("CRR", c, *at(clat, clon, -25, -40), "40th Street Metrolink", side="S", routes=["EB"])
cmo = add_stop("CMO", c, *at(clat, clon, 32, 9), "Telegraph Av / 40th", stop_id="DUP77", side="N", routes=["WB"])
cmr = add_stop("CMR", c, *at(clat, clon, 32, 9), "Telegraph Av / 40th", stop_id="DUP77", side="N", routes=["WB"])

# ---------- source keys and pairs ----------
for i, s in enumerate(stops):
    s["source_key"] = f"SRC_{i:05d}_{s['feed_key']}"
pairs = []
by_cluster = {}
for s in stops: by_cluster.setdefault(s["cluster"], []).append(s)
for cl, ss in by_cluster.items():
    for i in range(len(ss)):
        for k in range(i+1, len(ss)):
            a, b = ss[i], ss[k]
            if a["analysis_name"] == b["analysis_name"]: continue
            d = hav_ft((float(a["stop_lat"]), float(a["stop_lon"])), (float(b["stop_lat"]), float(b["stop_lon"])))
            if d > 300: continue
            pairs.append(dict(source_key_a=a["source_key"], source_key_b=b["source_key"], agency_a=a["analysis_name"], agency_b=b["analysis_name"],
                              feed_a=a["feed_name"], feed_b=b["feed_name"], stop_id_a=a["stop_id"], stop_id_b=b["stop_id"],
                              stop_name_a=a["stop_name"], stop_name_b=b["stop_name"], distance_ft=f"{d:.3f}",
                              relationship_id=f"REL{len(pairs):05d}"))

def write(path, rows, cols):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

def build(out_dir, seed_path, gdb):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    full_cols = ["stop_key","analysis_name","feed_name","feed_key","_gtfs_key","stop_id","stop_name","stop_code","stop_lat","stop_lon",
                 "stop_desc","tts_stop_name","parent_station","location_type","platform_code","route_types","regional_feed_type"]
    write(out/f"stops_curbside_analysis_{STAMP}.csv", stops, full_cols)
    cand = []
    for i, s in enumerate(stops):
        if i % 3 == 2: continue  # candidate file covers only part of the population
        cand.append(dict(stop_key=s["stop_key"], source_record_key=s["source_key"], direction_token=["", "NB", "WB", "SB"][i % 4],
            intersection_context_flag="Y", station_context_flag="N", shared_stop_group_id=f"OLDG{i//3}", shared_stop_recommendation="REVIEW",
            shared_stop_confidence="medium", shared_stop_operator_count="2", shared_stop_group_size="3", shared_stop_group_max_span_ft="40",
            shared_stop_caution_codes="", road_reference_eligible_pre="Y", road_safety_codes_pre="", selected_reference_flag="Y",
            selected_reference_source_key=s["source_key"], selected_reference_agency=s["analysis_name"], selected_reference_stop_id=s["stop_id"],
            selected_reference_lat=s["stop_lat"], selected_reference_lon=s["stop_lon"], reference_selection_method="OLD", reference_selection_score="50",
            reference_confidence="low", distance_to_reference_ft="12.5", over_25ft="N", verification_needed="N"))
    write(out/f"shared_stop_records_scored_{STAMP}.csv", cand, list(cand[0].keys()))
    write(out/f"shared_stop_pair_scores_{STAMP}.csv", pairs, list(pairs[0].keys()))
    write(out/f"shared_stop_groups_refined_{STAMP}.csv", [{"group_id": f"OLDG{i}"} for i in range(37)], ["group_id"])

    # served-shape cache (the complete cache is the first file the toolkit looks for)
    shp = []
    for s in stops:
        if s["code"] == "RAIL": continue
        lat, lon = float(s["stop_lat"]), float(s["stop_lon"])
        cl = [c for c in clusters if c[0] == s["cluster"]][0]; clat = cl[2] + s.get("shape_offset_ft", 0.0) * FT_LAT
        for r_i, rdir in enumerate(s["routes"]):
            bearing = 270.0 if rdir == "WB" else 90.0
            x0, x1 = (lon + 0.0006, lon - 0.0006) if rdir == "WB" else (lon - 0.0006, lon + 0.0006)
            for shape_n in range(2 if s["cluster"] % 5 == 0 else 1):
                jitter = 0.0 if shape_n == 0 else 4.0
                shp.append(dict(feed_key=s["feed_key"], stop_id=s["stop_id"], route_id=f"R{s['cluster']}{rdir}",
                    direction_id="0" if rdir == "WB" else "1", shape_id=f"SH{s['cluster']}{rdir}{shape_n}", service_date="2026-09-15",
                    feed_valid_from="2026-09-01 00:00:00", stop_to_shape_segment_ft=f"{abs(lat-clat)/FT_LAT:.2f}",
                    travel_bearing_deg=f"{bearing + jitter:.2f}", segment_start_lat=f"{clat:.7f}", segment_start_lon=f"{x0:.7f}",
                    segment_end_lat=f"{clat:.7f}", segment_end_lon=f"{x1:.7f}"))
    write(out/f"shared_stop_shape_context_shapes_complete_{STAMP}.csv", shp, list(shp[0].keys()))

    # road cache feature class seeded into the fake arcpy registry
    rows = []; oid = 0
    for (ci, kind, clat, clon, st, cr) in clusters:
        oid += 1; rows.append({"SHAPE@": {"paths": [[(clon-0.004, clat), (clon+0.004, clat)]]}, "ROAD_OID": 10000+oid, "RouteId": f"{st.upper()}_EW_{ci}"})
        oid += 1; rows.append({"SHAPE@": {"paths": [[(clon, clat-0.004), (clon, clat+0.004)]]}, "ROAD_OID": 10000+oid, "RouteId": f"{cr.upper()}_NS_{ci}"})
    fc = {"name": f"Caltrans_All_Roads_GTFS_Context_{STAMP}", "geom": "POLYLINE",
          "fields": [{"name": "ROAD_OID", "type": "LONG", "length": None, "alias": None}, {"name": "RouteId", "type": "TEXT", "length": 75, "alias": None}],
          "rows": rows}
    json.dump({os.path.join(gdb, fc["name"]): fc}, open(seed_path, "w"))
    print(f"stops={len(stops)} pairs={len(pairs)} shape_rows={len(shp)} roads={len(rows)}")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3])
