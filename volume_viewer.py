"""Local, in-memory volume exploration. Threshold preview is not organ segmentation."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import tempfile
import numpy as np


def load_nifti(data:bytes):
    import nibabel as nib
    if len(data)>100*1024*1024:raise ValueError("Compressed image is over 100 MB")
    path=None
    try:
        with tempfile.NamedTemporaryFile(suffix='.nii.gz',delete=False) as t:
            t.write(data);path=t.name
        img=nib.load(path)
        if len(img.shape)!=3 or np.prod(img.shape)>45_000_000:
            raise ValueError("Only a 3D study up to 45 million voxels is supported")
        return np.asarray(img.get_fdata(dtype=np.float32))
    finally:
        if path:Path(path).unlink(missing_ok=True)


def load_dicom_series(files: list[bytes]):
    import pydicom
    if not 2<=len(files)<=250:raise ValueError("Upload 2–250 slices from one series")
    if sum(map(len,files))>175*1024*1024:raise ValueError("Uploaded series is over 175 MB")
    slices=[];uids=set()
    for contents in files:
        ds=pydicom.dcmread(BytesIO(contents))
        if not hasattr(ds,'PixelData'):raise ValueError("Not an image DICOM file")
        uid=str(getattr(ds,'SeriesInstanceUID',''))
        if not uid:raise ValueError("Missing SeriesInstanceUID; cannot safely group series")
        uids.add(uid)
        values=ds.pixel_array.astype(np.float32)
        if values.ndim!=2:raise ValueError("Only single-frame monochrome DICOM slices are supported")
        values=values*float(getattr(ds,'RescaleSlope',1))+float(getattr(ds,'RescaleIntercept',0))
        coord=getattr(ds,'ImagePositionPatient',None)
        location=float(coord[2]) if coord is not None and len(coord)>2 else float(getattr(ds,'InstanceNumber',len(slices)))
        slices.append((location,values))
    if len(uids)!=1:raise ValueError("Files belong to different DICOM series")
    shape=slices[0][1].shape
    if any(arr.shape!=shape for _,arr in slices):raise ValueError("DICOM slices have different pixel shapes")
    if np.prod(shape)*len(slices)>45_000_000:raise ValueError("Series is too large for free memory")
    volume=np.stack([arr for _,arr in sorted(slices,key=lambda v:v[0])],axis=2)
    return volume


def preview_slice(volume,axis,index,low_pct=1,high_pct=99):
    if axis==0: z=volume[int(index),:,:]
    elif axis==1:z=volume[:,int(index),:]
    else:z=volume[:,:,int(index)]
    v=np.asarray(z,dtype=np.float32)
    lo,hi=np.percentile(v,[low_pct,high_pct])
    out=np.clip((v-lo)/(hi-lo+1e-6),0,1)
    return np.asarray(out*255,dtype=np.uint8)


def threshold_voxels(volume, min_value, max_value):
    """Interactive intensity mask; NOT pretrained AI or anatomically accurate segmentation."""
    return (np.asarray(volume)>=min_value)&(np.asarray(volume)<=max_value)
