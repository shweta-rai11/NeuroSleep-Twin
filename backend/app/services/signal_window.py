import numpy as np


def downsample_minmax(t: np.ndarray, v: np.ndarray, max_points: int) -> tuple[np.ndarray, np.ndarray]:
    """Bucket (t, v) into `max_points` buckets and keep each bucket's min and
    max sample (in time order). Plain mean decimation flattens spiky
    physiological waveforms (ECG QRS complexes, EEG transients); min/max
    keeps those visible at the cost of ~2x points versus a naive average.
    """
    n = len(v)
    if n <= max_points:
        return t, v

    bucket_edges = np.linspace(0, n, max_points + 1).astype(int)
    out_t: list[float] = []
    out_v: list[float] = []
    for lo, hi in zip(bucket_edges[:-1], bucket_edges[1:]):
        if hi <= lo:
            continue
        bucket_v = v[lo:hi]
        bucket_t = t[lo:hi]
        imin, imax = int(np.argmin(bucket_v)), int(np.argmax(bucket_v))
        for idx in sorted({imin, imax}):
            out_t.append(float(bucket_t[idx]))
            out_v.append(float(bucket_v[idx]))
    return np.array(out_t), np.array(out_v)
