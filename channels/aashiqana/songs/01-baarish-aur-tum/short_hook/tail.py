import numpy as np, soundfile as sf
for name,p in [("vox","short_hook/demucs/htdemucs/song/vocals.wav"),("inst","short_hook/demucs/htdemucs/song/no_vocals.wav")]:
    x,sr=sf.read(p,dtype="float32"); x=x.mean(1) if x.ndim>1 else x
    hop=int(sr*0.5); n=len(x)//hop
    e=np.sqrt((x[:n*hop].reshape(n,hop)**2).mean(1)+1e-12); db=20*np.log10(e/e.max())
    print(f"--- {name} (0.5s RMS, dB rel peak) 160..196s")
    print("   "+" ".join(f"{i*0.5:.0f}:{db[i]:.0f}" for i in range(int(160/0.5),int(196/0.5))))
