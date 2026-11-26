import itertools, json, sys
import model as M
from checks import vol
parts, comps = M.build_all()
phys = {k: v for k, v in comps.items() if not k.startswith('_')}
allp = {**parts, **phys}
moving = set(M.MOVING_PARTS) | set(M.MOVING_COMPS)
def allowed(a, b):
    return M.SCREW_HOSTS.get(a) == b or M.SCREW_HOSTS.get(b) == a
res = {}
for t in (M.CAM["tilt_min"], M.CAM["tilt"], M.CAM["tilt_max"]):
    cur = {k: (M.tilt_about_pivot(v, t) if k in moving else v) for k, v in allp.items()}
    bad = {}
    for a, b in itertools.combinations(cur, 2):
        if t != M.CAM["tilt"] and a not in moving and b not in moving:
            continue
        v = vol(cur[a], cur[b])
        if v > 0.001 and not allowed(a, b):
            bad[f"{a} ∩ {b}"] = round(v, 3)
    res[f"tilt={t:g}"] = bad
print(json.dumps(res, ensure_ascii=False, indent=1))
