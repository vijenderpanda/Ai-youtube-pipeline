import numpy as np, soundfile as sf
x,sr=sf.read("short_hook/demucs/htdemucs/song/vocals.wav",dtype="float32"); x=x.mean(1) if x.ndim>1 else x
hop=int(sr*0.25); n=len(x)//hop
e=np.sqrt((x[:n*hop].reshape(n,hop)**2).mean(1)+1e-12)
db=20*np.log10(e/e.max())
# contiguous vocal regions: db > -30
on = db > -30
segs=[];i=0
while i<n:
    if on[i]:
        j=i
        while j<n and on[j]: j+=1
        if (j-i)*0.25 >= 0.5: segs.append((i*0.25,j*0.25))
        i=j
    else: i+=1
# merge gaps < 0.75s
m=[]
for s in segs:
    if m and s[0]-m[-1][1] < 0.75: m[-1]=(m[-1][0], s[1])
    else: m.append(list(s) if False else (s[0],s[1]))
print("VOCAL-PRESENT REGIONS (>-30dB, merged):")
for s,e2 in m: print(f"  {s:7.2f} - {e2:7.2f}   ({e2-s:5.2f}s)")
print("\nSILENT (vocal) GAPS > 2s:")
prev=0.0
for s,e2 in m:
    if s-prev>2.0: print(f"  {prev:7.2f} - {s:7.2f}  ({s-prev:5.2f}s)")
    prev=e2
