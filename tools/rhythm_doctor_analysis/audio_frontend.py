"""Phase-safe stereo-to-mono frontend boundary."""
import numpy as np

def phase_safe_mono(audio, destructive_ratio=0.1):
    x=np.asarray(audio,dtype=np.float32)
    if x.ndim==1:return x.copy()
    if x.ndim!=2: raise ValueError('audio must be frames or frames-by-channels')
    mean=x.mean(axis=1); strongest=x[:,np.argmax(np.mean(x*x,axis=0))]
    mean_energy=float(np.mean(mean*mean)); channel_energy=float(np.max(np.mean(x*x,axis=0)))
    return strongest.copy() if channel_energy>0 and mean_energy/channel_energy<destructive_ratio else mean
