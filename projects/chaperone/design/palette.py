# Generates the "Black Box" palette scale (30/60% tints, tones, shades) and measures WCAG contrast.
# Run: python3 design/palette.py
def hx(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def tohex(c): return '#%02X%02X%02X'%tuple(round(x) for x in c)
def mix(a,b,t): return tuple(a[i]*(1-t)+b[i]*t for i in range(3))
def lum(c):
    def ch(v):
        v/=255; return v/12.92 if v<=0.03928 else ((v+0.055)/1.055)**2.4
    r,g,b=(ch(x) for x in c); return 0.2126*r+0.7152*g+0.0722*b
def cr(a,b):
    la,lb=sorted((lum(a),lum(b)),reverse=True); return (la+0.05)/(lb+0.05)
P={"Frost":"#D6E2EE","Steel":"#9DB4CC","Slate":"#62809F","Gunmetal":"#2F4358","Black Box":"#0E151D"}
W,G,K=(255,255,255),(128,128,128),(0,0,0)
print("## palette")
for n,h in P.items(): print(f"{n:10} {h}")
print("## derived (30/60%)")
scale={}
for n,h in P.items():
    c=hx(h)
    for kind,tgt in (("tint",W),("tone",G),("shade",K)):
        for t in (0.3,0.6):
            k=f"{n}-{kind}{int(t*100)}"; scale[k]=tohex(mix(c,tgt,t))
for k,v in scale.items(): print(f"{k:22} {v}")
# semantic tokens
bg=hx("#0E151D"); s1=hx(scale["Gunmetal-shade60"]); s2=hx(scale["Gunmetal-shade30"]); s3=hx("#2F4358")
print("## surfaces", tohex(bg), tohex(s1), tohex(s2), tohex(s3))
texts={"text (Frost)":"#D6E2EE","text-strong (Frost-tint60)":scale["Frost-tint60"],"muted (Steel)":"#9DB4CC","subtle (Steel-tone30)":scale["Steel-tone30"],"primary (Steel-tint30)":scale["Steel-tint30"],"Slate":"#62809F"}
status={"read/neutral":"#8FA3B8","write/info":"#6FB3E0","destructive/danger":"#F07A6E","escalation/warning":"#E8B45A","public/exposure":"#D98BD9","audit-tamper/critical":"#FF5C5C","ok/success":"#5CC8A0"}
print("## contrast vs surfaces (bg, surface1, surface2, surface3)")
for n,h in {**texts,**status}.items():
    c=hx(h); print(f"{n:28} {h}  " + "  ".join(f"{cr(c,s):5.2f}" for s in (bg,s1,s2,s3)))
