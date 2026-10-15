import math

import h3

H3_RESOLUTION = 8
CACHE_NEIGHBOR_RING = 1  


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometers."""
    r = 6371.0  # Earth radius, km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def latlng_to_h3(lat: float, lng: float, resolution: int = H3_RESOLUTION) -> str:
    """Returns the H3 cell index string containing this point."""
    return h3.latlng_to_cell(lat, lng, resolution)


def nearby_h3_cells(lat: float, lng: float, k: int = CACHE_NEIGHBOR_RING,
                     resolution: int = H3_RESOLUTION) -> list[str]:
    """Returns the H3 cell containing (lat, lng) plus its k-ring neighbors."""
    center = latlng_to_h3(lat, lng, resolution)
    return list(h3.grid_disk(center, k))

