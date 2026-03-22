"""Parser for mower vector map data from the Dreame batch device data API.

The batch API returns map data split across numbered keys (MAP.0, MAP.1, ...).
These chunks must be concatenated in numeric order to form a complete JSON string.
The JSON contains polygon-based zone boundaries, navigation paths, and metadata.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field

_LOGGER = logging.getLogger(__name__)

# Sentinel value in M_PATH data marking a path segment break
_PATH_SENTINEL = (32767, -32768)


@dataclass
class MowerZone:
    """A mowing zone defined by a polygon boundary."""
    zone_id: int
    path: list[tuple[int, int]]
    name: str = ""
    zone_type: int = 0
    shape_type: int = 0
    area: float = 0
    time: int = 0
    etime: int = 0


@dataclass
class MowerPath:
    """A navigation path between zones."""
    path_id: int
    path: list[tuple[int, int]]
    path_type: int = 0


@dataclass
class MowerContour:
    """A contour entry used for boundary or edge mowing."""
    contour_id: tuple[int, int]
    path: list[tuple[int, int]]
    contour_type: int = 0
    shape_type: int = 0


@dataclass
class MowerSpotArea:
    """A spot-mowing area defined by a polygon boundary."""

    area_id: int
    path: list[tuple[int, int]]
    name: str = ""
    shape_type: int = 0
    area: float = 0


@dataclass
class MowerAvailableMap:
    """A discovered map entry that can be targeted by map-aware mowing tasks."""

    map_id: int
    map_index: int
    name: str = ""
    total_area: float = 0


@dataclass
class MowerMapBoundary:
    """Bounding box for the entire map."""
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1


@dataclass
class MowerMowPath:
    """Mowing path trace — the actual trail the mower followed."""
    zone_id: int
    segments: list[list[tuple[int, int]]]


@dataclass
class MowerVectorMap:
    """Complete vector map data for a mower, fetched from batch API."""
    zones: list[MowerZone] = field(default_factory=list)
    spot_areas: list[MowerSpotArea] = field(default_factory=list)
    forbidden_areas: list[MowerZone] = field(default_factory=list)
    paths: list[MowerPath] = field(default_factory=list)
    contours: list[MowerContour] = field(default_factory=list)
    boundary: MowerMapBoundary | None = None
    total_area: float = 0
    name: str = ""
    map_id: int = 1
    map_index: int = 0
    mow_paths: list[MowerMowPath] = field(default_factory=list)
    available_maps: list[MowerAvailableMap] = field(default_factory=list)
    current_map_id: int | None = None
    last_updated: float | None = None


def _map_id_from_index(map_index: int) -> int:
    """Translate the batch map index into the task-level region identifier."""
    return map_index + 1


def reassemble_map_chunks(batch_data: dict, prefix: str) -> str | None:
    """Reassemble chunked data from batch API into a single string.

    Keys like MAP.0, MAP.1, ... MAP.N are concatenated in numeric order.
    The MAP.info key is skipped (it's metadata, not map content).

    Args:
        batch_data: dict from get_batch_device_datas response
        prefix: key prefix to match, e.g. "MAP" or "M_PATH"

    Returns:
        Concatenated string, or None if no matching keys found.
    """
    pattern = re.compile(rf"^{re.escape(prefix)}\.(\d+)$")
    chunks = []
    for key, value in batch_data.items():
        match = pattern.match(key)
        if match:
            chunks.append((int(match.group(1)), value))

    if not chunks:
        return None

    chunks.sort(key=lambda x: x[0])
    return "".join(value for _, value in chunks)


def _parse_polygon_list(data_map: dict) -> list:
    """Parse a dataType:Map structure containing polygon entries."""
    if not data_map or data_map.get("dataType") != "Map":
        return []
    return data_map.get("value", [])


def _extract_path_coords(path_list: list) -> list[tuple[int, int]]:
    """Convert [{"x": ..., "y": ...}, ...] to [(x, y), ...]."""
    return [(p["x"], p["y"]) for p in path_list]


def _extract_contour_id(raw_contour_id: list[int] | tuple[int, int]) -> tuple[int, int]:
    """Convert a contour identifier into a normalized two-integer tuple."""
    if len(raw_contour_id) != 2:
        raise ValueError(f"Invalid contour id: {raw_contour_id}")
    return (int(raw_contour_id[0]), int(raw_contour_id[1]))


def parse_mower_map(map_json_str: str) -> MowerVectorMap:
    """Parse a single map JSON string into a MowerVectorMap.

    Args:
        map_json_str: JSON string for one map (after unescaping from the chunk array).

    Returns:
        MowerVectorMap with zones, paths, boundary, etc.
    """
    data = json.loads(map_json_str)
    vmap = MowerVectorMap()

    # Parse mowing area zones
    for entry in _parse_polygon_list(data.get("mowingAreas", {})):
        zone_id, zone_data = entry[0], entry[1]
        vmap.zones.append(MowerZone(
            zone_id=zone_id,
            path=_extract_path_coords(zone_data.get("path", [])),
            name=zone_data.get("name", ""),
            zone_type=zone_data.get("type", 0),
            shape_type=zone_data.get("shapeType", 0),
            area=zone_data.get("area", 0),
            time=zone_data.get("time", 0),
            etime=zone_data.get("etime", 0),
        ))

    # Parse spot-mowing areas
    for entry in _parse_polygon_list(data.get("spotAreas", {})):
        area_id, area_data = entry[0], entry[1]
        vmap.spot_areas.append(MowerSpotArea(
            area_id=int(area_id),
            path=_extract_path_coords(area_data.get("path", [])),
            name=area_data.get("name", ""),
            shape_type=area_data.get("shapeType", 0),
            area=area_data.get("area", 0),
        ))

    # Parse forbidden areas
    for entry in _parse_polygon_list(data.get("forbiddenAreas", {})):
        zone_id, zone_data = entry[0], entry[1]
        vmap.forbidden_areas.append(MowerZone(
            zone_id=zone_id,
            path=_extract_path_coords(zone_data.get("path", [])),
            name=zone_data.get("name", ""),
            zone_type=zone_data.get("type", 0),
        ))

    # Parse navigation paths between zones
    for entry in _parse_polygon_list(data.get("paths", {})):
        path_id, path_data = entry[0], entry[1]
        vmap.paths.append(MowerPath(
            path_id=path_id,
            path=_extract_path_coords(path_data.get("path", [])),
            path_type=path_data.get("type", 0),
        ))

    # Parse contours used by edge mowing
    for entry in _parse_polygon_list(data.get("contours", {})):
        contour_id, contour_data = entry[0], entry[1]
        vmap.contours.append(MowerContour(
            contour_id=_extract_contour_id(contour_id),
            path=_extract_path_coords(contour_data.get("path", [])),
            contour_type=contour_data.get("type", 0),
            shape_type=contour_data.get("shapeType", 0),
        ))

    # Parse boundary
    boundary = data.get("boundary")
    if boundary:
        vmap.boundary = MowerMapBoundary(
            x1=boundary["x1"], y1=boundary["y1"],
            x2=boundary["x2"], y2=boundary["y2"],
        )

    vmap.total_area = data.get("totalArea", 0)
    vmap.name = data.get("name", "")
    vmap.map_index = data.get("mapIndex", 0)
    vmap.map_id = _map_id_from_index(vmap.map_index)
    vmap.last_updated = time.time()

    return vmap


def parse_mow_paths(batch_data: dict) -> list[MowerMowPath]:
    """Parse M_PATH.* keys from batch data into MowerMowPath objects.

    M_PATH data is chunked across numbered keys (M_PATH.0, M_PATH.1, ...)
    just like MAP data. The chunks must be reassembled into a single string.
    M_PATH.info contains the split position for multi-map data.

    The reassembled string contains [x,y] coordinate pairs with
    [32767,-32768] sentinels marking segment breaks.

    Args:
        batch_data: dict from get_batch_device_datas response

    Returns:
        List of MowerMowPath objects (one per zone, zone_id=0).
    """
    raw = reassemble_map_chunks(batch_data, "M_PATH")
    if not raw:
        return []

    # M_PATH.info is the split position (like MAP.info)
    info = batch_data.get("M_PATH.info", "")
    try:
        split_pos = int(info) if info.isdigit() else 0
    except (ValueError, AttributeError):
        split_pos = 0

    if split_pos > 0 and split_pos < len(raw):
        raw = raw[split_pos:]

    if not raw.strip() or raw.strip() == "[]":
        return []

    # Extract all [x,y] coordinate pairs using regex.
    # M_PATH coordinates are at 1/10th scale compared to zone coordinates
    # (decimeters vs centimeters), so we scale by 10 after sentinel detection.
    pair_pattern = re.compile(r"\[(-?\d+),(-?\d+)\]")
    raw_pairs = [(int(m.group(1)), int(m.group(2))) for m in pair_pattern.finditer(raw)]

    if not raw_pairs:
        return []

    # Split on sentinel into segments, then scale coordinates
    segments: list[list[tuple[int, int]]] = []
    current_segment: list[tuple[int, int]] = []
    for p in raw_pairs:
        if p == _PATH_SENTINEL:
            if current_segment:
                segments.append(current_segment)
                current_segment = []
        else:
            current_segment.append((p[0] * 10, p[1] * 10))

    if current_segment:
        segments.append(current_segment)

    if segments:
        return [MowerMowPath(zone_id=0, segments=segments)]

    return []


def vector_map_to_map_data(vector_map: MowerVectorMap) -> dict:
    """Convert a MowerVectorMap into the dict format expected by generate_svg_map_image.

    This bridges the batch API vector map data into the existing rendering pipeline
    so we don't need a separate SVG generator for vector maps.

    Returns:
        Dict with "map", "obstacle", "trajectory", and "start" keys.
    """
    # Build a lookup of mow_paths keyed by zone_id for fast matching
    mow_paths_by_zone: dict[int, MowerMowPath] = {}
    for mp in vector_map.mow_paths:
        mow_paths_by_zone.setdefault(mp.zone_id, mp)

    sentinel = [2147483647, 2147483647]

    map_items = []
    for zone in vector_map.zones:
        data = [[x, y] for x, y in zone.path]

        # Build track from matching mow_path segments, joined with sentinels
        track: list[list[int]] = []
        zone_mp = mow_paths_by_zone.get(zone.zone_id)
        if zone_mp:
            for i, seg in enumerate(zone_mp.segments):
                if i > 0:
                    track.append(sentinel)
                track.extend([x, y] for x, y in seg)

        map_items.append({
            "data": data,
            "track": track,
            "id": zone.zone_id,
            "name": zone.name,
            "area": zone.area,
        })

    # If mow_paths have zone_id=0 (unassigned), attach to all zones or as standalone
    mp_unassigned = mow_paths_by_zone.get(0)
    if mp_unassigned and not any(z.zone_id == 0 for z in vector_map.zones):
        track = []
        for i, seg in enumerate(mp_unassigned.segments):
            if i > 0:
                track.append(sentinel)
            track.extend([x, y] for x, y in seg)
        # Attach to first zone if it exists, otherwise create a standalone entry
        if map_items:
            map_items[0]["track"] = track
        else:
            map_items.append({"data": [], "track": track})

    obstacles = []
    for fa in vector_map.forbidden_areas:
        obstacles.append({
            "data": [[x, y] for x, y in fa.path],
            "id": fa.zone_id,
            "type": 0,
        })

    # Add navigation paths as type=1 map items (inter-zone connections)
    for nav_path in vector_map.paths:
        map_items.append({
            "data": [[x, y] for x, y in nav_path.path],
            "track": [],
            "id": nav_path.path_id,
            "name": "",
            "type": 1,
        })

    start = int(vector_map.last_updated) if vector_map.last_updated else 0

    return {
        "map": map_items,
        "obstacle": obstacles,
        "trajectory": [],
        "start": start,
    }


def parse_batch_map_data(batch_data: dict) -> MowerVectorMap | None:
    """Parse complete batch device data response into a MowerVectorMap.

    This is the main entry point. It:
    1. Reassembles MAP.* chunks into a full JSON string
    2. Parses the JSON array (may contain multiple maps by mapIndex)
    3. Returns the primary map (mapIndex 0)
    4. Attaches mowing paths from M_PATH.* keys

    Args:
        batch_data: Full response dict from get_batch_device_datas

    Returns:
        MowerVectorMap for the primary map, or None if parsing fails.
    """
    if not batch_data:
        return None

    raw_map = reassemble_map_chunks(batch_data, "MAP")
    if not raw_map:
        _LOGGER.debug("No MAP chunks found in batch data")
        return None

    # MAP.info contains the character length of the primary JSON array.
    # The full reassembled string may contain multiple JSON arrays
    # concatenated (one per map), so we use MAP.info to split them.
    map_info = batch_data.get("MAP.info", "")
    try:
        split_pos = int(map_info) if map_info.isdigit() else 0
    except (ValueError, AttributeError):
        split_pos = 0

    if split_pos > 0 and split_pos < len(raw_map):
        parts = [raw_map[:split_pos], raw_map[split_pos:]]
    else:
        parts = [raw_map]

    map_arrays = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        try:
            arr = json.loads(part)
            if isinstance(arr, list):
                map_arrays.extend(arr)
        except json.JSONDecodeError:
            _LOGGER.debug("Failed to parse MAP chunk part (len=%d)", len(part))

    if not map_arrays:
        _LOGGER.warning("No valid MAP arrays found in batch data")
        return None

    parsed_maps: list[MowerVectorMap] = []
    for map_json_str in map_arrays:
        try:
            parsed_maps.append(parse_mower_map(map_json_str))
        except (json.JSONDecodeError, KeyError, TypeError) as ex:
            _LOGGER.warning("Failed to parse map entry: %s", ex)
            continue

    primary_map = next((vmap for vmap in parsed_maps if vmap.map_index == 0), None)
    if primary_map is None and map_arrays:
        try:
            primary_map = parse_mower_map(map_arrays[0])
        except (json.JSONDecodeError, KeyError, TypeError) as ex:
            _LOGGER.warning("Failed to parse fallback map entry: %s", ex)
            return None

    if primary_map is None:
        return None

    primary_map.available_maps = [
        MowerAvailableMap(
            map_id=vmap.map_id,
            map_index=vmap.map_index,
            name=vmap.name,
            total_area=vmap.total_area,
        )
        for vmap in sorted(parsed_maps, key=lambda item: item.map_id)
    ]
    # Attach mowing paths
    primary_map.mow_paths = parse_mow_paths(batch_data)

    return primary_map
