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
    allowed = {}
    for a, b in itertools.combinations(allp, 2):
        v = vol(allp[a], allp[b])
        if v > 0.001:
            if M.SCREW_HOSTS.get(a) == b or M.SCREW_HOSTS.get(b) == a:
                allowed[f"{a} ∩ {b}"] = round(v, 3)     # 나사산·인서트가 파고드는 정상 부피
            else:
                inter[f"{a} ∩ {b}"] = round(v, 3)
    report["interference_mm3"] = inter
    report["screw_bite_mm3 (정상)"] = allowed

    # 2) 부품이 외피 밖으로 나가지 않는가 (버튼 머리는 원래 바깥)
    w, h, r = M.plan()
    env = M.rrect(w, h, r, 0, M.D, cy=M.H / 2).edges(">Z").fillet(M.F_FRONT).val()
    outside = {}
    for k, v in phys.items():
        if "(공간)" in k or k in ("ø4x25 접시 (벽)", "M3x16 (바닥 잠금)"):
            continue
        out = v.cut(env).Volume()
        if k == "16mm 호출벨":
            out -= M.cyl(M.BTN["head"] / 2, M.D, M.D + M.BTN["head_t"], M.BUTTON["cx"], M.BUTTON["cy"]).Volume()
        outside[k] = round(max(out, 0), 3)
    report["component_outside_envelope_mm3"] = outside

    # 3) 조립 경로: 쉘(+내장 부품)을 SLIDE 만큼 올려 벽으로 밀고(dz), 아래로 내려 끼운다(dy)
    shell_grp = [parts["01_front_shell"], parts["02_lcd_pi_chassis"], parts["04_black_visor"], parts["05_led_light_pipe"], parts["06_camera_holder"],
                 *[v for k, v in phys.items() if k not in ("ø4x25 접시 (벽)", "M3x16 (바닥 잠금)")]]
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
    # Camera Module 3 Wide 화각: 센서 기준 102° x 67° (Rev E 는 세로 장착이라 세로 102°) → 여유를 더한 사각뿔
    lh = M.CAM["height"] - M.CAM["pcb"] + 0.05
    gw, gh = L * math.tan(math.radians(53)), L * math.tan(math.radians(36))
    g0 = M.CAM["lens_glass"]
    cone = M.cam_place(M.frustum(g0, g0, 0.01, lh, g0 + 2 * gw, g0 + 2 * gh, 0.01, lh + L, 0, 0))
    tx, ty = M.TOF_POS
    sf = M.Z_IN - 0.2 + 0.05
    g = L * math.tan(math.radians(23.5))     # VL53L5CX 화각 45° + 여유 2°
    pyr = M.frustum(M.TOF["sens_w"], M.TOF["sens_h"], 0.01, sf,
                    M.TOF["sens_w"] + 2 * g, M.TOF["sens_h"] + 2 * g, 0.01, sf + L, tx, ty)
    blockers = parts["01_front_shell"].fuse(parts["04_black_visor"]).fuse(parts["06_camera_holder"])
    report["fov_blocked_mm3"] = {
        "tof_47x47": round(vol(pyr, blockers), 3),
    }
    # 카메라: 화각 가장자리(벽에 붙은 바닥)는 일부러 바이저 밖을 파지 않으므로,
    # 실제로 찍어야 하는 지점으로 가는 광선이 막히지 않는지 본다 (카메라 높이 1.4 m, 문은 정면에서 왼쪽)
    H0 = 1400.0
    targets = {"얼굴 160cm, 0.6m 앞": (0, 600, 1600 - H0), "정수리 175cm, 0.6m 앞": (0, 600, 1750 - H0),
               "바닥 0.5m 앞": (0, 500, -H0), "문 앞 바닥 (옆 0.6, 앞 0.4m)": (-600, 400, -H0),
               "문 앞 바닥 (옆 0.9, 앞 0.5m)": (-900, 500, -H0), "바닥 (옆 0.6, 앞 0.8m)": (-600, 800, -H0)}
    a_, b_ = math.radians(M.CAM["tilt"]), math.radians(M.CAM["yaw"])
    lens = V(M.CAM_POS[0], M.CAM_POS[1], M.LENS_FRONT_Z)
    rays = {}
    for n, (x, f, z) in targets.items():
        w = V(x, z, f).normalized()
        # 카메라 좌표로: yaw 되돌리고 tilt 되돌림
        cx = w.x * math.cos(b_) - w.z * math.sin(b_)
        cz0 = w.x * math.sin(b_) + w.z * math.cos(b_)
        cy = w.y * math.cos(a_) + cz0 * math.sin(a_)
        cz = -w.y * math.sin(a_) + cz0 * math.cos(a_)
        hdeg, vdeg = math.degrees(math.atan2(cx, cz)), math.degrees(math.atan2(cy, cz))
        seg = cq.Solid.makeCylinder(0.3, 40, lens + w * 0.6, w)
        rays[n] = {"in_fov": abs(hdeg) <= 33.5 and abs(vdeg) <= 51.0, "h_deg": round(hdeg, 1), "v_deg": round(vdeg, 1),
                   "blocked_mm3": round(vol(seg, blockers), 3)}
    report["camera_target_rays"] = rays
    report["camera"] = {"tilt_down_deg": M.CAM["tilt"], "yaw_deg": M.CAM["yaw"], "roll_deg": M.CAM["roll"],
                        "view_dir": [round(x, 3) for x in M.cam_dir().toTuple()]}

    # 4-1) 나사 물림 길이 (나사가 상대 재료/인서트 안에 들어간 길이, mm)
    f = M.FASTENERS
    ins = f["m3_insert"]
    report["screw_engagement_mm"] = {
        "M3x10 섀시 → 인서트(L4)": round(min(M.FRAME_BACK + 10.0, M.FRAME_FRONT + ins["length"]) - M.FRAME_FRONT, 2),
        "M3x10 끝 ~ 인서트 구멍 바닥 여유": round(M.FRAME_FRONT + ins["depth"] - (M.FRAME_BACK + 10.0), 2),
        "M2.5x6 Pi → 스탠드오프": round(M.PI_BOTTOM + 6.0 - M.PI_TOP, 2),
        "M2.5x6 스피커 → 보스 (앞판 2 가정)": round(6.0 - 2.0, 2),
        "M2x5 카메라 → 홀더": round(5.0 - M.CAM["pcb"], 2),
        "M3x16 바닥 → 브래킷 보스": round(1.2 + 16.0 - (M.T + M.CLEAR + M.SLIDE), 2),
        "M3x16 끝 ~ 보스 구멍 바닥 여유": round((M.T + M.CLEAR + M.SLIDE - 0.1 + 9.5) - (1.2 + 16.0), 2),
    }

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
