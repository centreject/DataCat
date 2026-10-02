"""모델 검증: 간섭, 조립 경로, 외피 안 수납, 카메라·ToF 화각 가림, 출력 가능성 지표"""
import itertools, json, math, time
import cadquery as cq
from cadquery import Vector as V
import model as M


def bb_overlap(a, b):
    A, B = a.BoundingBox(), b.BoundingBox()
    return not (A.xmax < B.xmin or B.xmax < A.xmin or A.ymax < B.ymin or B.ymax < A.ymin
                or A.zmax < B.zmin or B.zmax < A.zmin)


def vol(a, b):
    return a.intersect(b).Volume() if bb_overlap(a, b) else 0.0


def run():
    t = time.time()
    parts, comps = M.build_all()
    phys = {k: v for k, v in comps.items() if not k.startswith('_')}
    report = {"units": "mm", "overall_WxHxD": [M.W, M.H, M.D], "parts": {}, "components": {}}

    for k, v in parts.items():
        bb = v.BoundingBox()
        report["parts"][k] = {"valid": v.isValid(), "volume_cm3": round(v.Volume() / 1000, 2),
                              "bbox": [round(x, 2) for x in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)]}

    # 1) 모든 출력 부품 + 실제 부품 사이 간섭
    allp = {**parts, **phys}
    inter = {}
    for a, b in itertools.combinations(allp, 2):
        v = vol(allp[a], allp[b])
        if v > 0.001:
            inter[f"{a} ∩ {b}"] = round(v, 3)
    report["interference_mm3"] = inter

    # 2) 부품이 외피 밖으로 나가지 않는가 (버튼 머리는 원래 바깥)
    w, h, r = M.plan()
    env = M.rrect(w, h, r, 0, M.D, cy=M.H / 2).edges(">Z").fillet(M.F_FRONT).val()
    outside = {}
    for k, v in phys.items():
        out = v.cut(env).Volume()
        if k == "16mm 호출벨":
            out -= M.cyl(M.BTN["head"] / 2, M.D, M.D + M.BTN["head_t"], M.BUTTON["cx"], M.BUTTON["cy"]).Volume()
        outside[k] = round(max(out, 0), 3)
    report["component_outside_envelope_mm3"] = outside

    # 3) 조립 경로: 쉘(+내장 부품)을 SLIDE 만큼 올려 벽으로 밀고(dz), 아래로 내려 끼운다(dy)
    shell_grp = [parts["01_front_shell"], parts["02_lcd_pi_chassis"], parts["04_black_visor"], parts["05_led_light_pipe"],
                 *phys.values()]
    plate = parts["03_wall_plate"]
    path = []
    for dz in (12.0, 8.0, 4.0, 2.0, 0.0):
        path.append((M.SLIDE, dz))
    for dy in (6.0, 4.5, 3.0, 1.5, 0.0):
        path.append((dy, 0.0))
    motion = {}
    for dy, dz in path:
        tot = 0.0
        for s in shell_grp:
            tot += vol(s.translate(V(0, dy, dz)), plate)
        motion[f"dy={dy:+.1f}, dz={dz:+.1f}"] = round(tot, 3)
    report["mounting_path_collision_mm3"] = motion

    # 4) 카메라 화각(원뿔 60°)과 ToF 화각(45° x 45° 사각뿔)이 쉘·바이저에 가리지 않는가
    d = M.cam_dir()
    lens_c = V(M.CAM_POS[0], M.CAM_POS[1], M.LENS_FRONT_Z) + d * 0.05
    L = 30.0
    # Camera Module 3 Wide 화각: 수평 102°, 수직 67° → 여유 2~3° 를 더한 사각뿔
    lh = M.CAM["height"] - M.CAM["pcb"] + 0.05
    gw, gh = L * math.tan(math.radians(53)), L * math.tan(math.radians(36))
    g0 = M.CAM["lens_glass"]
    cone = M.cam_place(M.frustum(g0, g0, 0.01, lh, g0 + 2 * gw, g0 + 2 * gh, 0.01, lh + L, 0, 0))
    tx, ty = M.TOF_POS
    sf = M.Z_IN - 0.2 + 0.05
    g = L * math.tan(math.radians(22.5))
    pyr = M.frustum(M.TOF["sens_w"], M.TOF["sens_h"], 0.01, sf,
                    M.TOF["sens_w"] + 2 * g, M.TOF["sens_h"] + 2 * g, 0.01, sf + L, tx, ty)
    blockers = parts["01_front_shell"].fuse(parts["04_black_visor"])
    report["fov_blocked_mm3"] = {
        "camera_H106_V72": round(vol(cone, blockers), 3),
        "tof_45x45": round(vol(pyr, blockers), 3),
    }
    report["camera_tilt_deg"] = M.CAM["tilt"]

    # 5) 화면이 창에서 잘리지 않는가 (활성 영역 vs 창)
    report["screen"] = {"active_mm": [M.LCD["act_w"], M.LCD["act_h"]],
                        "window_mm": [M.WINDOW["w"], M.WINDOW["h"]],
                        "margin_each_side_mm": [round((M.WINDOW["w"] - M.LCD["act_w"]) / 2, 2),
                                                round((M.WINDOW["h"] - M.LCD["act_h"]) / 2, 2)]}

    # 6) 깊이 방향 적층표
    report["z_stack_mm"] = {
        "front_face": M.D, "front_inner_face": M.Z_IN,
        "lcd_glass_front": M.LCD_FRONT, "lcd_pcb_back": M.LCD_PCB_BACK,
        "chassis": [M.FRAME_BACK, M.FRAME_FRONT],
        "pi_component_side": M.PI_TOP, "pi_solder_side": M.PI_BOTTOM,
        "wall_plate": [0, M.PLATE_T], "camera_lens_front": M.LENS_FRONT_Z,
    }
    report["build_seconds"] = round(time.time() - t, 1)
    return report, parts, comps


if __name__ == "__main__":
    rep, *_ = run()
    print(json.dumps(rep, ensure_ascii=False, indent=1))
