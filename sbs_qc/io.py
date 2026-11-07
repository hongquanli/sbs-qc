"""OME-TIFF loading with base-channel mapping from channel names."""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
import numpy as np
import tifffile

BASES = ("A", "C", "T", "G")
_BASE_SUFFIX = re.compile(r"(?:^|[-_\s])([ACGT])\s*$")
_DAPI = re.compile(r"dapi|405", re.I)


@dataclass
class Stack:
    """A multi-channel field: data is (C, Y, X) uint16 as stored."""
    data: np.ndarray
    names: list[str]
    base_idx: dict[str, int]
    dapi_idx: int | None = None
    pixel_um: float | None = None
    path: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def base(self) -> np.ndarray:
        """(4, Y, X) float32 in the fixed order A, C, T, G."""
        return np.stack([self.data[self.base_idx[b]] for b in BASES]).astype(np.float32)

    @property
    def dapi(self) -> np.ndarray | None:
        return None if self.dapi_idx is None else self.data[self.dapi_idx].astype(np.float32)


def map_channels(names: list[str]) -> tuple[dict[str, int], int | None]:
    """Map channel names to bases by a trailing ' - A' style token; DAPI by name or 405."""
    base_idx: dict[str, int] = {}
    dapi = None
    for i, n in enumerate(names):
        m = _BASE_SUFFIX.search(n.strip())
        if m and m.group(1) not in base_idx:
            base_idx[m.group(1)] = i
        elif dapi is None and _DAPI.search(n):
            dapi = i
    missing = [b for b in BASES if b not in base_idx]
    if missing:
        raise ValueError(f"could not map channels {missing} from names {names}; pass --channels explicitly")
    return base_idx, dapi


def _ome_channel_names(xml: str | None) -> tuple[list[str], float | None]:
    if not xml:
        return [], None
    root = ET.fromstring(xml)
    ns = {"ome": root.tag.split("}")[0].strip("{")} if root.tag.startswith("{") else {}
    pix = root.find(".//ome:Pixels", ns) if ns else root.find(".//Pixels")
    names, px = [], None
    if pix is not None:
        for ch in (pix.findall("ome:Channel", ns) if ns else pix.findall("Channel")):
            names.append(ch.get("Name") or ch.get("ID") or "")
        if pix.get("PhysicalSizeX"):
            px = float(pix.get("PhysicalSizeX"))
    return names, px


def load_ome(path: str, channels: str | list[str] | None = None) -> Stack:
    """Load an OME-TIFF (C, Y, X). `channels` overrides names, e.g. "A,C,T,G,DAPI"."""
    with tifffile.TiffFile(path) as tf:
        data = tf.asarray()
        names, px = _ome_channel_names(tf.ome_metadata)
    if data.ndim == 2:
        data = data[None]
    if data.ndim != 3:
        data = data.reshape(-1, *data.shape[-2:])
    if channels is not None:
        names = channels.split(",") if isinstance(channels, str) else list(channels)
        names = [n.strip() for n in names]
    if len(names) != data.shape[0]:
        names = (names + [f"ch{i}" for i in range(data.shape[0])])[: data.shape[0]]
    base_idx, dapi = map_channels(names)
    return Stack(data=data, names=names, base_idx=base_idx, dapi_idx=dapi, pixel_um=px, path=path)
