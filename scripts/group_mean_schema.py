"""Shared on-disk group schema; importing queries does not load the analysis pipeline."""
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/group_means'
DTYPE = np.dtype([
    ('closure_lo', '<u8'), ('closure_hi', '<u8'),
    ('generator_lo', '<u8'), ('generator_hi', '<u8'),
    ('n', '<u4'), ('low_n', '<u4'), ('equal_n', '<u4'),
    ('development_n', '<u4'), ('test_n', '<u4'), ('reserved', '<u4'),
    ('ratio_sum', '<f8'), ('ratio_sq_sum', '<f8'),
    ('development_sum', '<f8'), ('test_sum', '<f8'),
])
