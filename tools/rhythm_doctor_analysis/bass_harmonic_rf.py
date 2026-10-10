"""BASS-only harmonic-attack feature architecture; no corpus split or held scorer."""
from __future__ import annotations
import numpy as np

FFT_SIZE=2048
HOP=.020

def phase_safe_mono(audio):
    values=np.asarray(audio,dtype=np.float32)
    if values.ndim == 1: return values
    if values.ndim != 2 or values.shape[1] < 1: raise ValueError('invalid audio')
    mean=values.mean(axis=1); channel_energy=np.mean(values*values,axis=0); strongest=values[:,int(np.argmax(channel_energy))]
    return strongest if np.max(channel_energy)>0 and np.mean(mean*mean)/np.max(channel_energy)<.1 else mean

def feature_matrix(audio,sample_rate,hop=HOP):
    """Bounded offline features for bass attack candidates, one row per hop."""
    if sample_rate <= 0: raise ValueError('invalid sample rate')
    signal=phase_safe_mono(audio); half=FFT_SIZE//2; window=np.hanning(FFT_SIZE); frequencies=np.fft.rfftfreq(FFT_SIZE,1/sample_rate)
    duration=len(signal)/sample_rate; times=np.arange(.05,max(.05,duration-.05),hop)
    edges=np.geomspace(25,6000,25); masks=[(frequencies>=low)&(frequencies<high) for low,high in zip(edges[:-1],edges[1:])]
    low=(frequencies>=25)&(frequencies<250); mid=(frequencies>=250)&(frequencies<2000); high=(frequencies>=2000)&(frequencies<6000)
    rows=[]; previous=None
    for moment in times:
        center=int(moment*sample_rate); frame=signal[max(0,center-half):min(len(signal),center+half)]
        frame=np.pad(frame,(max(0,half-center),max(0,FFT_SIZE-len(frame)-max(0,half-center))))[:FFT_SIZE]
        magnitude=np.abs(np.fft.rfft(frame*window)); bands=np.log1p(np.array([magnitude[mask].sum() for mask in masks]))
        delta=bands-(previous if previous is not None else bands); previous=bands
        total=magnitude.sum()+1e-9; low_energy=magnitude[low].sum(); mid_energy=magnitude[mid].sum(); high_energy=magnitude[high].sum()
        positive_delta=np.maximum(delta,0); low_delta=positive_delta[:np.searchsorted(edges,250,side='left')].sum();
        harmonic=[]
        for fundamental in (41.2,49.,55.,65.4,73.4,82.4,98.,110.,130.8,146.8,164.8,196.):
            harmonic.append(sum(magnitude[np.argmin(abs(frequencies-fundamental*multiple))] for multiple in (1,2,3,4,5)))
        centroid=(frequencies*magnitude).sum()/total/6000
        flatness=float(np.exp(np.mean(np.log(magnitude+1e-9)))/(np.mean(magnitude)+1e-9))
        rows.append(np.r_[bands,delta,np.log1p([low_energy,mid_energy,high_energy]),low_energy/total,low_energy/(mid_energy+1e-9),low_delta/(positive_delta.sum()+1e-9),max(harmonic)/total,centroid,flatness])
    base=np.asarray(rows,dtype=np.float32)
    if not len(base): return times,np.empty((0,0),dtype=np.float32)
    return times,np.c_[np.vstack((base[0],base[:-1])),base,np.vstack((base[1:],base[-1]))]
