"""
Road context from Caltrans All Roads centerlines.

Adds road-centerline context for the records in groups that have a stop
location issue or an unresolved location. Road context is not shared-stop
evidence: it never changes the Shared Stop Score, pair grouping, the
operator-majority recommendation, or the >25-ft issue flags.

Where it is used:
  * road distance feeds RoadDistFt / FarthestRoad / TieBreakRec, a
    post-scoring tie-break for locations with no normal recommendation;
  * road_context_ambiguous (more than one nearby road alignment) is one of the
    boarding-position clues in the two-agency recommendation: a stop with a
    single unambiguous nearby roadway gets +1 point there.

Cache note: the road extract is cached as a feature class named
Caltrans_All_Roads_GTFS_Context_{source_run_stamp} with fields ROAD_OID and
RouteId. Keeping a stable cache schema allows later runs to reuse the extract
without querying the live service again.
"""
from collections import defaultdict
from pathlib import Path
import json, math, os, time, urllib.parse, urllib.request
import pandas as pd

road_service_url = "https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/All_Roads/FeatureServer/0"
road_query_url = road_service_url + "/query"
tile_size_m = 5000.0
tile_expand_m = 300.0
near_search_ft = 500.0
intersection_context_ft = 150.0
max_record_count = 2000

def _clean(v):
    if v is None: return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan","none","null"} else s

def _safe_float(v):
    try: return float(v)
    except Exception: return None

def _post_json(url, params, attempts=3, timeout=60):
    data = urllib.parse.urlencode(params).encode("utf-8")
    last = None
    for attempt in range(1, attempts+1):
        try:
            req = urllib.request.Request(url, data=data, headers={
                "User-Agent":"California-GTFS-Shared-Stop-QA/1.0",
                "Content-Type":"application/x-www-form-urlencoded",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = json.loads(r.read().decode("utf-8"))
            if "error" in payload:
                raise RuntimeError("ArcGIS REST error: " + json.dumps(payload["error"], ensure_ascii=False))
            return payload
        except Exception as exc:
            last = exc
            if attempt < attempts: time.sleep(1.5*attempt)
    raise RuntimeError(f"Road service request failed after {attempts} attempts: {last}")

def _validate_road_service():
    p = _post_json(road_service_url, {"f":"json"})
    if p.get("geometryType") != "esriGeometryPolyline":
        raise RuntimeError("Caltrans All Roads geometry is not polyline as expected.")
    fields = {f.get("name") for f in p.get("fields",[])}
    missing = {"OBJECTID","RouteId"} - fields
    if missing:
        raise RuntimeError("Caltrans All Roads missing required field(s): " + ", ".join(sorted(missing)))
    return p

def _project_points_to_california_albers(records):
    """Project stop points to California Albers (EPSG:3310) for tiling."""
    import arcpy
    sr4326, sr3310 = arcpy.SpatialReference(4326), arcpy.SpatialReference(3310)
    rows = []
    for idx,row in records.iterrows():
        lat,lon = _safe_float(row.get("GTFS_stop_lat")), _safe_float(row.get("GTFS_stop_lon"))
        if lat is None or lon is None: continue
        p = arcpy.PointGeometry(arcpy.Point(lon,lat), sr4326).projectAs(sr3310).firstPoint
        rows.append((idx,float(p.X),float(p.Y)))
    return rows

def _find_occupied_tiles(rows):
    return sorted({(math.floor(x/tile_size_m), math.floor(y/tile_size_m)) for _,x,y in rows})

def _query_road_tile(tx,ty):
    xmin,ymin = tx*tile_size_m-tile_expand_m, ty*tile_size_m-tile_expand_m
    xmax,ymax = (tx+1)*tile_size_m+tile_expand_m, (ty+1)*tile_size_m+tile_expand_m
    out=[]; offset=0
    while True:
        p = _post_json(road_query_url, {
            "f":"json","where":"1=1","geometry":f"{xmin},{ymin},{xmax},{ymax}",
            "geometryType":"esriGeometryEnvelope","inSR":"3310",
            "spatialRel":"esriSpatialRelIntersects","outFields":"OBJECTID,RouteId",
            "returnGeometry":"true","outSR":"3310","returnZ":"false","returnM":"false",
            "resultOffset":str(offset),"resultRecordCount":str(max_record_count),
        })
        batch = p.get("features",[]); out.extend(batch)
        if not p.get("exceededTransferLimit") and len(batch) < max_record_count: break
        if not batch: break
        offset += len(batch)
    return out

def _write_road_cache(out_gdb,name,features):
    import arcpy
    out_fc=os.path.join(str(out_gdb),name)
    if arcpy.Exists(out_fc): arcpy.management.Delete(out_fc)
    sr=arcpy.SpatialReference(3310)
    arcpy.management.CreateFeatureclass(str(out_gdb),name,"POLYLINE",has_z="DISABLED",has_m="DISABLED",spatial_reference=sr)
    arcpy.management.AddField(out_fc,"ROAD_OID","LONG")
    arcpy.management.AddField(out_fc,"RouteId","TEXT",field_length=75)
    n=0
    with arcpy.da.InsertCursor(out_fc,["SHAPE@","ROAD_OID","RouteId"]) as cur:
        for oid,feature in features.items():
            paths=(feature.get("geometry") or {}).get("paths") or []
            if not paths: continue
            arrays=arcpy.Array()
            for path in paths:
                arrays.add(arcpy.Array([arcpy.Point(float(x),float(y)) for x,y in path]))
            attrs=feature.get("attributes") or {}
            cur.insertRow([arcpy.Polyline(arrays,sr),int(attrs.get("OBJECTID") or oid),_clean(attrs.get("RouteId"))])
            n += 1
    print(f"[roads] cached {n:,} unique road features: {out_fc}")
    return out_fc

def _build_relevant_road_records(final_scored,issue_records,unresolved):
    gids=set()
    if issue_records is not None and not issue_records.empty:
        gids.update(issue_records["shared_stop_group_id"].astype(str).str.strip())
    if unresolved is not None and not unresolved.empty:
        gids.update(unresolved["shared_stop_group_id"].astype(str).str.strip())
    gids.discard("")
    return final_scored[final_scored["shared_stop_group_id"].astype(str).isin(gids)].copy() if gids else pd.DataFrame(columns=final_scored.columns)

def _write_road_context_points(out_gdb,name,records):
    import arcpy
    out_fc=os.path.join(str(out_gdb),name)
    if arcpy.Exists(out_fc): arcpy.management.Delete(out_fc)
    arcpy.management.CreateFeatureclass(str(out_gdb),name,"POINT",spatial_reference=arcpy.SpatialReference(4326))
    for fn,ln in [("src_key",64),("group_id",64),("agency",255),("stop_id",100),("stop_name",500)]:
        arcpy.management.AddField(out_fc,fn,"TEXT",field_length=ln)
    n=0
    with arcpy.da.InsertCursor(out_fc,["SHAPE@XY","src_key","group_id","agency","stop_id","stop_name"]) as cur:
        for _,r in records.iterrows():
            lat,lon=_safe_float(r.get("GTFS_stop_lat")),_safe_float(r.get("GTFS_stop_lon"))
            if lat is None or lon is None: continue
            cur.insertRow([(lon,lat),_clean(r.get("source_key"))[:64],_clean(r.get("shared_stop_group_id"))[:64],_clean(r.get("agency_name"))[:255],_clean(r.get("GTFS_stop_id"))[:100],_clean(r.get("GTFS_stop_name"))[:500]])
            n += 1
    print(f"[roads] wrote relevant GTFS points: {out_fc}; inserted={n:,}")
    return out_fc

def _calculate_near_metrics(points_fc,roads_fc):
    import arcpy
    near_table=os.path.join(arcpy.env.scratchGDB,"gtfs_road_near")
    if arcpy.Exists(near_table): arcpy.management.Delete(near_table)
    arcpy.analysis.GenerateNearTable(points_fc,roads_fc,near_table,f"{near_search_ft} Feet","NO_LOCATION","NO_ANGLE","ALL",5,"GEODESIC","Feet")
    road_attrs={}
    with arcpy.da.SearchCursor(roads_fc,["OID@","ROAD_OID","RouteId"]) as c:
        for oid,road_oid,routeid in c: road_attrs[int(oid)]={"road_oid":road_oid,"route_id":_clean(routeid)}
    point_source={}
    with arcpy.da.SearchCursor(points_fc,["OID@","src_key"]) as c:
        for oid,src in c: point_source[int(oid)]=_clean(src)
    hits=defaultdict(list)
    with arcpy.da.SearchCursor(near_table,["IN_FID","NEAR_FID","NEAR_DIST","NEAR_RANK"]) as c:
        for infid,nfid,dist,rank in c:
            src=point_source.get(int(infid),"")
            if not src: continue
            r=road_attrs.get(int(nfid),{})
            hits[src].append({"near_rank":int(rank),"distance_ft":float(dist),"road_oid":r.get("road_oid"),"route_id":r.get("route_id","")})
    rows=[]
    for src,vals in hits.items():
        vals=sorted(vals,key=lambda x:(x["near_rank"],x["distance_ft"])); nearest=vals[0]
        within=[x for x in vals if x["distance_ft"]<=intersection_context_ft]
        routes=sorted({x["route_id"] for x in within if x["route_id"]})
        rows.append({"source_key":src,"road_nearest_distance_ft":round(nearest["distance_ft"],2),"road_nearest_route_id":nearest["route_id"],"road_nearest_objectid":nearest["road_oid"],"road_segments_within_150ft":len(within),"road_route_ids_within_150ft":" | ".join(routes),"road_distinct_route_ids_within_150ft":len(routes),"road_context_ambiguous":"Y" if len(routes)>1 else "N"})
    return pd.DataFrame(rows)

def _build_road_group_summary(records):
    rows=[]
    if records.empty: return pd.DataFrame()
    for gid,g in records.groupby("shared_stop_group_id",sort=False):
        routes=sorted({_clean(v) for v in g.get("road_nearest_route_id",pd.Series(dtype=str)).tolist() if _clean(v)})
        dists=pd.to_numeric(g.get("road_nearest_distance_ft",pd.Series(dtype=float)),errors="coerce").dropna()
        amb=g.get("road_context_ambiguous",pd.Series("",index=g.index)).astype(str).eq("Y").sum()
        if not routes: status="NO_ROAD_MATCH_WITHIN_500FT"
        elif len(routes)==1 and amb==0: status="SINGLE_NEAREST_ROUTE_CONTEXT"
        elif amb>0: status="INTERSECTION_OR_MULTI_ROAD_CONTEXT"
        else: status="MULTIPLE_NEAREST_ROUTE_ALIGNMENTS"
        rows.append({"shared_stop_group_id":gid,"road_context_status":status,"road_context_record_count":len(g),"road_records_with_match":int(g["road_nearest_distance_ft"].notna().sum()),"road_distinct_nearest_route_ids":len(routes),"road_nearest_route_ids":" | ".join(routes),"road_max_nearest_distance_ft":round(float(dists.max()),2) if len(dists) else "","road_mean_nearest_distance_ft":round(float(dists.mean()),2) if len(dists) else "","road_ambiguous_record_count":int(amb)})
    return pd.DataFrame(rows)

def _annotate_issues_with_road_context(issues,metrics):
    if issues is None or issues.empty: return issues
    lookup=metrics.set_index("source_key").to_dict("index") if metrics is not None and not metrics.empty else {}
    out=issues.copy(); vals=[]
    for _,r in out.iterrows():
        im=lookup.get(_clean(r.get("likely_incorrect_source_key")),{}); rm=lookup.get(_clean(r.get("recommended_source_key")),{})
        ir,rr=_clean(im.get("road_nearest_route_id")),_clean(rm.get("road_nearest_route_id"))
        vals.append((im.get("road_nearest_distance_ft",""),ir,rm.get("road_nearest_distance_ft",""),rr,"Y" if ir and rr and ir==rr else ("N" if ir and rr else ""),"SAME_NEAREST_ALL_ROADS_ROUTE" if ir and rr and ir==rr else ("DIFFERENT_NEAREST_ALL_ROADS_ROUTE" if ir and rr else "ROAD_CONTEXT_INCOMPLETE")))
    cols=["issue_road_nearest_distance_ft","issue_road_nearest_route_id","recommended_road_nearest_distance_ft","recommended_road_nearest_route_id","issue_and_recommended_same_nearest_route_id","issue_road_context_status"]
    for i,c in enumerate(cols): out[c]=[v[i] for v in vals]
    return out

def run_road_context(final_scored,issue_records,unresolved_locations,out_gdb,source_run_stamp,reuse_cache=True,validate_service=True):
    import arcpy
    meta=_validate_road_service() if validate_service else {"name":"All Roads (service check skipped: cached context run)"}
    print(f"[roads] service OK: {meta.get('name','All Roads')}; maxRecordCount={meta.get('maxRecordCount')}; wkid={(meta.get('extent') or {}).get('spatialReference',{}).get('wkid')}")
    relevant=_build_relevant_road_records(final_scored,issue_records,unresolved_locations)
    print(f"[roads] relevant GTFS records for road review: {len(relevant):,} across {relevant['shared_stop_group_id'].nunique():,} groups")
    if relevant.empty:
        return {"final_scored":final_scored,"issue_records":issue_records,"unresolved_locations":unresolved_locations,"road_record_context":pd.DataFrame(),"road_group_context":pd.DataFrame(),"roads_feature_class":None,"points_feature_class":None}
    road_name=f"Caltrans_All_Roads_GTFS_Context_{source_run_stamp}"; road_fc=os.path.join(str(out_gdb),road_name)
    if reuse_cache and arcpy.Exists(road_fc):
        print(f"[roads] reusing cached road extract: {road_fc}")
    else:
        tiles=_find_occupied_tiles(_project_points_to_california_albers(relevant)); print(f"[roads] occupied 5-km query tiles: {len(tiles):,}")
        unique={}
        for i,(tx,ty) in enumerate(tiles,1):
            for f in _query_road_tile(tx,ty):
                oid=(f.get("attributes") or {}).get("OBJECTID")
                if oid is not None: unique[int(oid)]=f
            if i%25==0 or i==len(tiles): print(f"[roads] queried {i:,}/{len(tiles):,} tiles; unique roads={len(unique):,}")
        road_fc=_write_road_cache(out_gdb,road_name,unique)
    points_fc=_write_road_context_points(out_gdb,"road_context_points",relevant)
    metrics=_calculate_near_metrics(points_fc,road_fc)
    relevant=relevant.merge(metrics,on="source_key",how="left")
    groups=_build_road_group_summary(relevant)
    road_cols=[c for c in ["source_key","road_nearest_distance_ft","road_nearest_route_id","road_nearest_objectid","road_segments_within_150ft","road_route_ids_within_150ft","road_distinct_route_ids_within_150ft","road_context_ambiguous"] if c in relevant.columns]
    fs=final_scored.copy()
    for c in road_cols:
        if c!="source_key" and c in fs.columns: fs=fs.drop(columns=[c])
    fs=fs.merge(relevant[road_cols],on="source_key",how="left")
    issues=_annotate_issues_with_road_context(issue_records,metrics)
    unresolved=unresolved_locations.copy()
    if unresolved is not None and not unresolved.empty and not groups.empty:
        unresolved=unresolved.merge(groups,on="shared_stop_group_id",how="left")
    return {"final_scored":fs,"issue_records":issues,"unresolved_locations":unresolved,"road_record_context":relevant,"road_group_context":groups,"roads_feature_class":road_fc,"points_feature_class":points_fc}
