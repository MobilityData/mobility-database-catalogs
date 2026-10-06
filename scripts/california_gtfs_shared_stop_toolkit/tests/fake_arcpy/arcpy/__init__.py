"""Minimal in-memory stand-in for arcpy, used only by the end-to-end test.

Stores feature classes in a registry (schema + rows) so a test run's
geodatabase layers can be compared with the expected layers.
GenerateNearTable is implemented with a simple planar distance in feet so the road
context code runs end to end. Not a real GIS engine.
"""
import json, math, os, types

_registry = {}   # path(lower) -> {"name","geom","fields":[{name,type,length,alias}],"rows":[dict]}

def _key(p): return os.path.normpath(str(p)).lower()

def _load_seed():
    seed = os.environ.get("FAKE_ARCPY_SEED")
    if seed and os.path.exists(seed):
        data = json.load(open(seed))
        for path, fc in data.items():
            _registry[_key(path)] = fc
_load_seed()

def dump(path):
    json.dump(_registry, open(path, "w"), default=str, indent=1, sort_keys=True)

class SpatialReference:
    def __init__(self, wkid=None): self.factoryCode = wkid
class Point:
    def __init__(self, X=0.0, Y=0.0): self.X, self.Y = X, Y
class Array(list):
    def add(self, x): self.append(x)
class Polyline:
    def __init__(self, arr, sr=None):
        parts = list(arr)
        if parts and isinstance(parts[0], Point): parts = [parts]
        self.paths = [[(p.X, p.Y) for p in part] for part in parts]
class PointGeometry:
    def __init__(self, pt, sr=None): self.firstPoint = pt
    def projectAs(self, sr): return self

def Exists(p): return _key(p) in _registry

class _Env: scratchGDB = "/tmp/fake_scratch.gdb"
env = _Env()

def _field_index(fc, name):
    for i, f in enumerate(fc["fields"]):
        if f["name"].lower() == name.lower(): return i
    raise RuntimeError(f"Field not found: {name} in {fc['name']}")

class _Mgmt:
    def Delete(self, p): _registry.pop(_key(p), None)
    def CreateFileGDB(self, folder, name): os.makedirs(os.path.join(folder, name), exist_ok=True)
    def CreateFeatureclass(self, gdb, name, geom, **kw):
        _registry[_key(os.path.join(str(gdb), name))] = {"name": name, "geom": geom, "fields": [], "rows": []}
    def AddField(self, fc, name, ftype, field_length=None, field_alias=None, **kw):
        f = _registry[_key(fc)]
        f["fields"].append({"name": name, "type": ftype, "length": field_length, "alias": field_alias})
    def AddFields(self, fc, specs):
        for s in specs:
            self.AddField(fc, s[0], s[1], field_alias=s[2] if len(s) > 2 else None, field_length=s[3] if len(s) > 3 else None)
    def Copy(self, src, dst):
        import copy
        fc = copy.deepcopy(_registry[_key(src)]); fc["name"] = os.path.basename(str(dst)); _registry[_key(dst)] = fc
    def AlterField(self, fc, name, new_field_alias=None, **kw):
        f = _registry[_key(fc)]; f["fields"][_field_index(f, name)]["alias"] = new_field_alias
management = _Mgmt()

class InsertCursor:
    def __init__(self, fc, fields):
        self.fc = _registry[_key(fc)]; self.fields = fields
        for n in fields:
            if not n.upper().startswith("SHAPE@"): _field_index(self.fc, n)
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def insertRow(self, values):
        row = {}
        for n, v in zip(self.fields, values):
            if n.upper() == "SHAPE@" and isinstance(v, Polyline): v = {"paths": v.paths}
            row[n.upper() if n.upper().startswith("SHAPE@") else self.fc["fields"][_field_index(self.fc, n)]["name"]] = v
        self.fc["rows"].append(row)

class SearchCursor:
    def __init__(self, fc, fields):
        self.fc = _registry[_key(fc)]; self.fields = fields
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __iter__(self):
        for i, row in enumerate(self.fc["rows"], 1):
            out = []
            for n in self.fields:
                if n.upper() == "OID@": out.append(i)
                elif n.upper().startswith("SHAPE@"): out.append(row.get(n.upper()))
                else: out.append(row.get(self.fc["fields"][_field_index(self.fc, n)]["name"]))
            yield tuple(out)
da = types.SimpleNamespace(InsertCursor=InsertCursor, SearchCursor=SearchCursor)

def _seg_dist_ft(px, py, a, b):
    # lon/lat -> local feet (planar approximation; deterministic test geometry only)
    kx = 364000.0 * math.cos(math.radians(py)); ky = 364000.0
    ax, ay = (a[0]-px)*kx, (a[1]-py)*ky; bx, by = (b[0]-px)*kx, (b[1]-py)*ky
    dx, dy = bx-ax, by-ay; L = dx*dx+dy*dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, -(ax*dx+ay*dy)/L))
    cx, cy = ax+t*dx, ay+t*dy
    return math.hypot(cx, cy)

class _Analysis:
    def GenerateNearTable(self, in_fc, near_fc, out_table, radius, loc, ang, closest, count, method, unit):
        pts = _registry[_key(in_fc)]; roads = _registry[_key(near_fc)]
        r = float(str(radius).split()[0])
        out = {"name": "near", "geom": "TABLE", "fields": [{"name": n, "type": "DOUBLE", "length": None, "alias": None} for n in ["IN_FID","NEAR_FID","NEAR_DIST","NEAR_RANK"]], "rows": []}
        for i, p in enumerate(pts["rows"], 1):
            px, py = p["SHAPE@XY"]
            cands = []
            for j, rd in enumerate(roads["rows"], 1):
                d = min(_seg_dist_ft(px, py, path[k], path[k+1]) for path in rd["SHAPE@"]["paths"] for k in range(len(path)-1))
                if d <= r: cands.append((round(d, 6), j))
            cands.sort()
            for rank, (d, j) in enumerate(cands[:int(count)], 1):
                out["rows"].append({"IN_FID": i, "NEAR_FID": j, "NEAR_DIST": d, "NEAR_RANK": rank})
        _registry[_key(out_table)] = out
analysis = _Analysis()

class _Map:
    def addDataFromPath(self, p): pass
class _Project:
    def __init__(self, x): self.defaultGeodatabase = None
    def listMaps(self): return [_Map()]
    @property
    def activeMap(self): return _Map()
mp = types.SimpleNamespace(ArcGISProject=_Project)
