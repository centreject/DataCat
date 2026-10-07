import asyncio, sys, subprocess, time
from playwright.async_api import async_playwright
import model as M
LABELS = [
  [-20, 177, M.LENS_FRONT_Z - 6, 'Camera Module 3 Wide (10° 아래로)', -230, 10, 'end'],
  [-20, 168, M.D - 0.6, '블랙 바이저', 130, -70],
  [-20, 110, M.LCD_PCB_BACK + 2, '3.5인치 HDMI LCD', 160, -40],
  [-20, 100, M.FRAME_BACK + 1, 'LCD·Pi 섀시', -230, 20, 'end'],
  [-20, 125, M.PI_TOP + 6, 'Raspberry Pi 4 (2×13 스태킹)', -230, -60, 'end'],
  [-8, 30, 20, '16mm 호출벨', -200, 40, 'end'],
  [-20, 60, 1.5, '벽 브래킷', -150, 40, 'end'],
  [-20, 189, 5.2, '걸이 갈고리', -150, -40, 'end'],
]
views = sys.argv[1:] or ['hero','front','side','exploded','xray','back','section&x=-20']
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8765'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
            pg = await b.new_page(viewport={'width':1600,'height':1200})
            pg.on('console', lambda m: print('console:', m.text) if m.type in ('error','warning') else None)
            pg.on('pageerror', lambda e: print('pageerror:', e))
            for v in views:
                from urllib.parse import quote
                vv = v
                if v.startswith('section'):
                    import json as _j
                    vv = v + '&labels=' + quote(_j.dumps(LABELS, ensure_ascii=False))
                await pg.goto(f'http://localhost:8765/render.html?view={vv}')
                await pg.wait_for_function('window.DONE === true', timeout=240000)
                name = v.split('&')[0]
                await pg.screenshot(path=f'out/{name}.png')
                print('shot', name)
            await b.close()
    finally:
        srv.terminate()
asyncio.run(main())
