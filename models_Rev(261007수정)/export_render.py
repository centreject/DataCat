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
       "Camera Module 3 Wide":"c_cam","VL53L5CX ToF":"c_tof","USB 마이크 동글":"c_umic","USB 스피커 플러그":"c_uplug","USB 스피커 보드":"c_uboard",
       "HDMI FPC 케이블(공간)":"c_hdmi","GPIO 27~40 배선(공간)":"c_gpio_keep",
       "USB 스피커 유닛 ø28":"c_spk","16mm 호출벨":"c_btn","상태 LED":"c_led",
       "_cam_lens":"c_cam_lens","_cam_board":"c_cam_board","_tof_sensor":"c_tof_sensor","_tof_board":"c_tof_board"}
for k,v in comps.items(): ex(k, v, ids[k])
names["_screen"] = {"cx": M.WINDOW["cx"], "cy": M.WINDOW["cy"], "z": M.LCD_FRONT + 0.02, "w": M.LCD["act_w"], "h": M.LCD["act_h"], "D": M.D}
json.dump(names, open('out/render/index.json','w'), ensure_ascii=False, indent=1)
print(names)
