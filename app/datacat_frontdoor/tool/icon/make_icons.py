import cairosvg, io
from PIL import Image, ImageChops
BG='#1E5B52'; CREAM='#F4F1EA'; KNOB='#E0A84A'
BODY='M356 790 L356 352 L392 236 L478 318 L546 318 L632 236 L668 352 L668 790 Z'
def shape(fill, details=True, s=1.0, floor=True):
    g=f'<g transform="translate(512 520) scale({s}) translate(-512 -520)">'
    g+=f'<path d="{BODY}" fill="{fill}" stroke="{fill}" stroke-width="36" stroke-linejoin="round"/>'
    if floor:
        g+=f'<rect x="286" y="812" width="452" height="26" rx="13" fill="{fill}" opacity="0.55"/>'
    if details:
        g+=f'<ellipse cx="454" cy="470" rx="20" ry="28" fill="{BG}"/><ellipse cx="570" cy="470" rx="20" ry="28" fill="{BG}"/>'
        g+=f'<circle cx="624" cy="610" r="22" fill="{KNOB}"/>'
    return g+'</g>'
def holes(s):
    g=f'<g transform="translate(512 520) scale({s}) translate(-512 -520)">'
    g+='<ellipse cx="454" cy="470" rx="24" ry="32" fill="#000"/><ellipse cx="570" cy="470" rx="24" ry="32" fill="#000"/><circle cx="624" cy="610" r="26" fill="#000"/>'
    return g+'</g>'
def svg(body,bg=None,radius=0):
    b=f'<rect width="1024" height="1024" rx="{radius}" fill="{bg}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">{b}{body}</svg>'
def png(s,size=1024):
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=s.encode(),output_width=size,output_height=size))).convert('RGBA')
out={}
out['icon_full']=svg(shape(CREAM),BG,0)
out['icon_rounded']=svg(shape(CREAM),BG,230)
out['icon_fg']=svg(shape(CREAM,s=0.8))
for n,s in out.items():
    open(n+'.svg','w').write(s); png(s).save(n+'.png')
# notification: white silhouette with eyes/knob punched out
sil=png(svg(shape('#FFFFFF',details=False,s=1.12,floor=False)))
h=png(svg(holes(1.12)))
a=ImageChops.subtract(sil.getchannel('A'),h.getchannel('A'))
noti=Image.new('RGBA',sil.size,(255,255,255,0)); noti.putalpha(a)
noti.save('icon_noti.png')
