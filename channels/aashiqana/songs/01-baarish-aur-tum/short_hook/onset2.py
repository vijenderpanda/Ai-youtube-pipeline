import numpy as np, soundfile as sf, sys
VOX="short_hook/demucs/htdemucs/song/vocals.wav"
x,sr=sf.read(VOX,dtype="float32"); x=x.mean(1) if x.ndim>1 else x
hop=int(sr*0.02); n=len(x)//hop
e=np.sqrt((x[:n*hop].reshape(n,hop)**2).mean(1)+1e-12); fps=sr/hop
db=20*np.log10(e/ (e.max()+1e-12))
def show(t,pre=2.0,post=1.2):
    a,b=int((t-pre)*fps),int((t+post)*fps)
    floor=np.percentile(db[max(0,int((t-4)*fps)):b],10)
    thr=floor+12
    # first sustained (100ms) crossing above thr searching forward from t-pre
    sus=int(0.10*fps); on=None
    for i in range(a,b-sus):
        if (db[i:i+sus]>thr).all(): on=i/fps; break
    print(f"\n== target {t:.2f}s  floor {floor:.1f}dB thr {thr:.1f}dB  ONSET={on if on is None else round(on,3)}")
    print("   " + " ".join(f"{(i/fps):.2f}:{db[i]:.0f}" for i in range(a,b,5)))
for t in [float(v) for v in sys.argv[1:]]: show(t)
