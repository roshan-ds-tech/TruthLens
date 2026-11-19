"""A small offline gazetteer (§3.6) used to compare place claims with EXIF GPS. Coordinates are city centres."""
from __future__ import annotations

import math

PLACES: dict[str, tuple[float, float]] = {
    "Chennai": (13.0827, 80.2707), "Bengaluru": (12.9716, 77.5946), "Bangalore": (12.9716, 77.5946),
    "Mumbai": (19.0760, 72.8777), "Delhi": (28.6139, 77.2090), "New Delhi": (28.6139, 77.2090),
    "Kolkata": (22.5726, 88.3639), "Hyderabad": (17.3850, 78.4867), "Pune": (18.5204, 73.8567),
    "Ahmedabad": (23.0225, 72.5714), "Jaipur": (26.9124, 75.7873), "Lucknow": (26.8467, 80.9462),
    "Kochi": (9.9312, 76.2673), "Thiruvananthapuram": (8.5241, 76.9366), "Coimbatore": (11.0168, 76.9558),
    "Madurai": (9.9252, 78.1198), "Mysuru": (12.2958, 76.6394), "Mysore": (12.2958, 76.6394),
    "Mangaluru": (12.9141, 74.8560), "Visakhapatnam": (17.6868, 83.2185), "Vijayawada": (16.5062, 80.6480),
    "Bhubaneswar": (20.2961, 85.8245), "Patna": (25.5941, 85.1376), "Guwahati": (26.1445, 91.7362),
    "Chandigarh": (30.7333, 76.7794), "Bhopal": (23.2599, 77.4126), "Indore": (22.7196, 75.8577),
    "Nagpur": (21.1458, 79.0882), "Surat": (21.1702, 72.8311), "Goa": (15.2993, 74.1240),
    "Puducherry": (11.9416, 79.8083), "Srinagar": (34.0837, 74.7973), "Dehradun": (30.3165, 78.0322),
    "Ranchi": (23.3441, 85.3096), "Raipur": (21.2514, 81.6296), "Shimla": (31.1048, 77.1734),
    "Tamil Nadu": (11.1271, 78.6569), "Karnataka": (15.3173, 75.7139), "Kerala": (10.8505, 76.2711),
    "London": (51.5074, -0.1278), "New York": (40.7128, -74.0060), "Dubai": (25.2048, 55.2708),
    "Singapore": (1.3521, 103.8198),
}


def lookup(name: str) -> tuple[float, float] | None:
    for k, v in PLACES.items():
        if k.lower() == name.strip().lower():
            return v
    return None


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))
