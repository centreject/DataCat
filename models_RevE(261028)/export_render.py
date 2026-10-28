import json, os
import cadquery as cq
import model as M
parts, comps = M.build_all()
os.makedirs('out/render', exist_ok=True)
names = {}
def ex(key, shape, fname):
    cq.exporters.export(cq.Workplane().add(shape), f'out/render/{fname}.stl', tolerance=0.04, angularTolerance=0.08)
    names[key]=fname
for k,v in parts.items(): ex(k, v, k)
ids = {"Raspberry Pi 4":"c_pi","USB-C L형 플러그":"c_usbc","3.5인치 HDMI LCD":"c_lcd","_LCD 화면":"c_screen",
       "Camera Module 3 Wide":"c_cam","VL53L0X ToF":"c_tof","ToF 핀헤더·듀폰(공간)":"c_tof_hdr","USB 핀마이크":"c_umic",
       "MAX98357A 앰프":"c_amp","HDMI FPC 케이블(공간)":"c_hdmi","GPIO 27~40 배선(공간)":"c_gpio_keep",
       "스피커 ø28":"c_spk","16mm 호출벨":"c_btn","상태 LED":"c_led",
       "_cam_lens":"c_cam_lens","_cam_board":"c_cam_board","_tof_sensor":"c_tof_sensor","_tof_board":"c_tof_board",
       "M3x10 (섀시)":"c_scr_m3","M3 인서트":"c_insert","M2.5x6 태핑 (Pi)":"c_scr_m25","M2x5 태핑 (카메라)":"c_scr_m2",
       "M3x16 (바닥 잠금)":"c_scr_bottom","ø4x25 접시 (벽)":"c_scr_wall"}
for k,v in comps.items(): ex(k, v, ids[k])
names["_screen"] = {"cx": M.WINDOW["cx"], "cy": M.WINDOW["cy"], "z": M.LCD_FRONT + 0.02, "w": M.LCD["act_w"], "h": M.LCD["act_h"], "D": M.D, "H": M.H}
json.dump(names, open('out/render/index.json','w'), ensure_ascii=False, indent=1)
print(names)
