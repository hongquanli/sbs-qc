"""Base-separability QC for sequencing-by-synthesis (SBS) in situ images.

Pipeline: load OME-TIFF -> background / smoothing / foreground -> block features
-> dye signature matrix -> NNLS unmixing -> chastity + base calls -> figures.
"""
from .io import Stack, load_ome
from .features import BlockFeatures, block_features, channel_stats
from .signatures import mixing_angles, seed_groups, signature_matrix, contrast_ratios, signature_angles
from .unmix import unmix, chastity, call_bases
from .registration import channel_shifts

BASES = ("A", "C", "T", "G")
__all__ = ["Stack", "load_ome", "BlockFeatures", "block_features", "channel_stats", "mixing_angles", "seed_groups",
           "signature_matrix", "contrast_ratios", "signature_angles", "unmix", "chastity", "call_bases", "channel_shifts", "BASES"]
