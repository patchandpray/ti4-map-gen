#!/usr/bin/env python3
"""Build the Operation Puzzled Energy map from the Magi's Madness preset.

System art is Milty's flat-top tile set. Columns are vertical (flat edges stack).
Odd columns sit half a step lower. Hyperlane rotation is left at 0 for now.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TILE_IMG = "https://milty.shenanigans.be/img/tiles/ST_{id}.png"
FACTION_IMG = "https://milty.shenanigans.be/img/factions/ti_{id}.png"
REFERENCE_IMG = "https://milty.shenanigans.be/img/reference/r_{id}.jpg"

DRAFT = {
    "id": "20261027_84b2c85b5936a1ae",
    "name": "Operation Puzzled Energy",
    "source": "https://milty.shenanigans.be/d/20261027_84b2c85b5936a1ae?fresh=1#draft",
    "seed": 330649319188752,
    "mecatol": "18",
    "preset": "Magi's Madness",
    "notes": "7-player preset from Twilight Codex Volume II. Milty slices are not used. Seats are the named home positions; factions are still being drafted.",
}

# Flat-top odd-column grid. (column, row). Confirmed on the version-3 overlay.
# Hyperlane rotation is 0 until we set it.
SYSTEMS = [
    ("29", 4, 0), ("80", 5, 0), ("50", 6, 0), ("67", 7, 0), ("33", 8, 0),
    ("91B", 3, 1, 1), ("H:non", 4, 1), ("88B", 5, 1, 2), ("26", 6, 1), ("44", 7, 1), ("H:pain", 8, 1),
    ("28", 2, 2), ("45", 3, 2), ("62", 4, 2), ("42", 5, 2), ("90B", 6, 2, 1), ("37", 7, 2), ("22", 8, 2),
    ("H:ambassador", 1, 3), ("64", 2, 3), ("75", 3, 3), ("70", 4, 3), ("84A", 5, 3, 2), ("36", 6, 3), ("66", 7, 3), ("87B", 8, 3, 3),
    ("24", 0, 4), ("49", 1, 4), ("74", 2, 4), ("H:hold", 3, 4), ("85A", 4, 4, 2), ("H:mountain", 5, 4), ("27", 6, 4), ("25", 7, 4), ("86A", 8, 4, 5),
    ("72", 0, 5), ("79", 1, 5), ("76", 2, 5), ("69", 3, 5), ("83A", 4, 5, 2), ("34", 5, 5), ("43", 6, 5), ("73", 7, 5),
    ("47", 0, 6), ("61", 1, 6), ("46", 2, 6), ("68", 3, 6), ("65", 4, 6), ("48", 5, 6), ("H:lava", 6, 6),
    ("H:frontier", 0, 7), ("35", 1, 7), ("78", 2, 7), ("M", 3, 7), ("19", 4, 7), ("38", 5, 7),
    ("59", 0, 8), ("41", 1, 8), ("40", 2, 8), ("39", 3, 8), ("77", 4, 8),
]

HOMES = {
    "non": {"name": "Non-Euclidean", "color": "#1abc9c"},
    "ambassador": {"name": "Ambassador", "color": "#5dade2"},
    "pain": {"name": "Pain Train", "color": "#e74c3c"},
    "hold": {"name": "Why Can't I Hold All", "color": "#f39c12"},
    "mountain": {"name": "Mountain Fortress", "color": "#27ae60"},
    "frontier": {"name": "Final Frontier", "color": "#85929e"},
    "lava": {"name": "The Floor is Lava", "color": "#e67e22"},
}

# Draft order on the milty page. Only Paul has picked so far.
PLAYERS = [
    {"order": 1, "name": "Paul", "faction": "The Federation of Sol", "claimed": True, "color": "#9b59b6"},
    {"order": 2, "name": "Sander", "faction": None, "claimed": False, "color": "#e84393", "turn": True},
    {"order": 3, "name": "Rens", "faction": None, "claimed": False, "color": "#e67e22"},
    {"order": 4, "name": "Lars", "faction": None, "claimed": True, "color": "#ecf0f1"},
    {"order": 5, "name": "Tim", "faction": None, "claimed": True, "color": "#2ecc71"},
    {"order": 6, "name": "Arie", "faction": None, "claimed": False, "color": "#5dade2"},
    {"order": 7, "name": "Ruben", "faction": None, "claimed": False, "color": "#f1c40f"},
]

FACTION_POOL = [
    "The Ghosts of Creuss",
    "The Winnu",
    "Sardakk N'orr",
    "The L1z1x Mindnet",
    "The Yssaril Tribes",
    "The Federation of Sol",
    "The Mentak Coalition",
    "The Xxcha Kingdom",
    "The Naaz-Rokha Alliance",
]

# Flat-top image edge indexes used by tiles.json, clockwise from the top edge.
# After a +30 degree turn these land on pointy-top neighbors, clockwise from NE.
POINTY_DIRS = [(1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1)]

AXIAL_DIRS = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]


def axial_ring(radius: int) -> list[tuple[int, int]]:
    q, r = 0, -radius
    results = []
    for i in range(6):
        for _ in range(radius):
            results.append((q, r))
            dq, dr = AXIAL_DIRS[i]
            q += dq
            r += dr
    return results


def cube_ring(q: int, r: int) -> int:
    s = -q - r
    return max(abs(q), abs(r), abs(s))


def pixel(q: int, r: int, size: float) -> tuple[float, float]:
    x = size * 1.5 * q
    y = size * math.sqrt(3) * (r + 0.5 * (q % 2))
    return x, y


def hex_corners(cx: float, cy: float, size: float) -> list[tuple[float, float]]:
    pts = []
    for i in range(6):
        angle = math.radians(60 * i)
        pts.append((cx + size * math.cos(angle), cy + size * math.sin(angle)))
    return pts


def optimal_pair(resources: float, influence: float) -> tuple[float, float]:
    if resources == influence:
        return resources / 2, influence / 2
    if resources > influence:
        return resources, 0.0
    return 0.0, influence


def trait_text(trait) -> str:
    if not trait:
        return ""
    if isinstance(trait, list):
        return "+".join(trait)
    return str(trait)


def summarize_tile(tile_id: str, catalog: dict) -> dict:
    raw = catalog.get(str(tile_id), {})
    planets = []
    resources = influence = 0
    opt_r = opt_i = 0.0
    specialties = []
    legendaries = []
    for planet in raw.get("planets") or []:
        res = planet.get("resources") or 0
        inf = planet.get("influence") or 0
        resources += res
        influence += inf
        o_r, o_i = optimal_pair(res, inf)
        opt_r += o_r
        opt_i += o_i
        specs = planet.get("specialties") or []
        specialties.extend(specs)
        legendary = planet.get("legendary")
        if legendary:
            legendaries.append(planet["name"])
        planets.append(
            {
                "name": planet.get("name"),
                "resources": res,
                "influence": inf,
                "trait": trait_text(planet.get("trait")),
                "legendary": bool(legendary),
                "legendary_text": legendary if isinstance(legendary, str) else "",
                "specialties": specs,
            }
        )
    stations = []
    for station in raw.get("stations") or []:
        res = station.get("resources") or 0
        inf = station.get("influence") or 0
        resources += res
        influence += inf
        o_r, o_i = optimal_pair(res, inf)
        opt_r += o_r
        opt_i += o_i
        stations.append({"name": station.get("name"), "resources": res, "influence": inf})
    label_parts = [p["name"] for p in planets] + [s["name"] for s in stations]
    if not label_parts:
        if raw.get("anomaly"):
            label_parts = [str(raw["anomaly"])]
        elif raw.get("wormhole"):
            label_parts = [f"{raw['wormhole']} wormhole"]
        elif raw.get("type") == "hyperlane":
            label_parts = ["Hyperlane"]
        else:
            label_parts = ["Empty space"]
    return {
        "tile_id": str(tile_id),
        "type": raw.get("type"),
        "set": raw.get("set"),
        "wormhole": raw.get("wormhole"),
        "anomaly": raw.get("anomaly"),
        "hyperlanes": raw.get("hyperlanes") or [],
        "planets": planets,
        "stations": stations,
        "resources": resources,
        "influence": influence,
        "optimal_resources": opt_r,
        "optimal_influence": opt_i,
        "specialties": specialties,
        "legendaries": legendaries,
        "system_label": " / ".join(label_parts),
        "image_url": TILE_IMG.format(id=tile_id),
    }


def parse_system(entry: tuple) -> tuple[str, int, int, int]:
    if len(entry) == 4:
        tile, q, r, turn = entry
    else:
        tile, q, r = entry
        turn = 0
    return tile, q, r, turn


def build(catalog: dict, factions: dict) -> dict:
    placed = [parse_system(e) for e in SYSTEMS]
    coords = {(q, r) for _, q, r, _ in placed}
    hexes = []
    for tile, q, r, turn in placed:
        is_mecatol = tile == "M"
        is_home = tile.startswith("H:")
        home_key = tile[2:] if is_home else None
        home = HOMES.get(home_key or "")
        if is_mecatol:
            summary = summarize_tile(DRAFT["mecatol"], catalog)
            summary["system_label"] = "Mecatol Rex"
        elif is_home:
            summary = summarize_tile("0", catalog)
            summary["tile_id"] = "0"
            summary["type"] = "green"
            summary["system_label"] = home["name"]
            summary["image_url"] = TILE_IMG.format(id="0")
        else:
            summary = summarize_tile(tile, catalog)
        hexes.append(
            {
                **summary,
                "q": q,
                "r": r,
                "s": -q - r,
                "ring": cube_ring(q, r),
                "rotation": turn,
                "image_rotation": 60 * turn,
                "is_home": is_home,
                "is_mecatol": is_mecatol,
                "is_hyperlane": summary["type"] == "hyperlane",
                "position": home["name"] if home else None,
                "position_key": home_key,
                "color": home["color"] if home else ("#f4d03f" if is_mecatol else None),
                "player": None,
                "seat": None,
                "faction": None,
            }
        )

    by_coord = {(h["q"], h["r"]): h for h in hexes}
    for h in hexes:
        neighbors = []
        for dq, dr in AXIAL_DIRS:
            n = by_coord.get((h["q"] + dq, h["r"] + dr))
            if n:
                neighbors.append(n["tile_id"] if not n["is_home"] else n["position"])
        h["neighbor_labels"] = neighbors

    # TTS spiral around Mecatol. Absent hexes are 0, matching Milty.
    tts_tiles = [DRAFT["mecatol"]]
    max_ring = max(h["ring"] for h in hexes)
    tts_coords = []
    for radius in range(1, max_ring + 1):
        tts_coords.extend(axial_ring(radius))
    for i, h in enumerate(hexes):
        h["tts_index"] = 0 if (h["q"], h["r"]) == (0, 0) else None
    for i, (q, r) in enumerate(tts_coords, start=1):
        h = by_coord.get((q, r))
        if h is None:
            tts_tiles.append("0")
        else:
            h["tts_index"] = i
            token = h["tile_id"]
            if h["is_hyperlane"]:
                token = f"{token}{h['rotation']}"
            tts_tiles.append(token)

    players_out = []
    for player in PLAYERS:
        faction = factions.get(player["faction"] or "")
        players_out.append(
            {
                **player,
                "faction_id": faction["id"] if faction else None,
                "homesystem": faction["homesystem"] if faction else None,
                "wiki": faction["wiki"] if faction else None,
                "reference_url": REFERENCE_IMG.format(id=faction["id"]) if faction else None,
                "icon_url": FACTION_IMG.format(id=faction["id"]) if faction else None,
                "position": None,
            }
        )

    pool = []
    picked = {p["faction"] for p in PLAYERS if p["faction"]}
    for name in FACTION_POOL:
        faction = factions[name]
        pool.append(
            {
                "name": name,
                "faction_id": faction["id"],
                "wiki": faction["wiki"],
                "homesystem": faction["homesystem"],
                "icon_url": FACTION_IMG.format(id=faction["id"]),
                "reference_url": REFERENCE_IMG.format(id=faction["id"]),
                "picked": name in picked,
                "picked_by": next((p["name"] for p in PLAYERS if p["faction"] == name), None),
            }
        )

    positions = []
    for h in hexes:
        if not h["is_home"]:
            continue
        adj = []
        res = inf = 0
        for dq, dr in AXIAL_DIRS:
            n = by_coord.get((h["q"] + dq, h["r"] + dr))
            if not n:
                continue
            adj.append(n)
            res += n["resources"]
            inf += n["influence"]
        positions.append(
            {
                "key": h["position_key"],
                "name": h["position"],
                "color": h["color"],
                "q": h["q"],
                "r": h["r"],
                "adjacent": [a["system_label"] for a in adj],
                "resources": res,
                "influence": inf,
            }
        )

    return {
        "draft": DRAFT,
        "players": players_out,
        "positions": positions,
        "hexes": hexes,
        "tts_map_string": " ".join(tts_tiles),
        "factions": pool,
        "coords_check": len(coords),
    }


def write_csv(map_data: dict) -> None:
    path = DATA / "map.csv"
    fields = [
        "tts_index",
        "q",
        "r",
        "s",
        "ring",
        "tile_id",
        "system_label",
        "position",
        "planets",
        "stations",
        "resources",
        "influence",
        "optimal_resources",
        "optimal_influence",
        "wormhole",
        "anomaly",
        "specialties",
        "legendaries",
        "tile_type",
        "tile_set",
        "is_home",
        "is_mecatol",
        "is_hyperlane",
        "rotation",
        "image_url",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        rows = sorted(
            map_data["hexes"],
            key=lambda h: (h["tts_index"] is None, h["tts_index"] if h["tts_index"] is not None else 99, h["q"], h["r"]),
        )
        for h in rows:
            writer.writerow(
                {
                    "tts_index": "" if h["tts_index"] is None else h["tts_index"],
                    "q": h["q"],
                    "r": h["r"],
                    "s": h["s"],
                    "ring": h["ring"],
                    "tile_id": h["tile_id"],
                    "system_label": h["system_label"],
                    "position": h["position"] or "",
                    "planets": "; ".join(
                        f"{p['name']} {p['resources']}/{p['influence']}"
                        + (f" {p['trait']}" if p["trait"] else "")
                        + (" legendary" if p["legendary"] else "")
                        + (f" tech:{','.join(p['specialties'])}" if p["specialties"] else "")
                        for p in h["planets"]
                    ),
                    "stations": "; ".join(f"{s['name']} {s['resources']}/{s['influence']}" for s in h["stations"]),
                    "resources": h["resources"],
                    "influence": h["influence"],
                    "optimal_resources": h["optimal_resources"],
                    "optimal_influence": h["optimal_influence"],
                    "wormhole": h["wormhole"] or "",
                    "anomaly": h["anomaly"] or "",
                    "specialties": ", ".join(h["specialties"]),
                    "legendaries": ", ".join(h["legendaries"]),
                    "tile_type": h["type"] or "",
                    "tile_set": h["set"] or "",
                    "is_home": str(h["is_home"]).lower(),
                    "is_mecatol": str(h["is_mecatol"]).lower(),
                    "is_hyperlane": str(h["is_hyperlane"]).lower(),
                    "rotation": h["rotation"],
                    "image_url": h["image_url"],
                }
            )
    (DATA / "tts-map-string.txt").write_text(map_data["tts_map_string"] + "\n", encoding="utf-8")


def write_json(map_data: dict) -> None:
    payload = {k: v for k, v in map_data.items() if k != "coords_check"}
    (DATA / "map.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (DATA / "map.js").write_text("window.MAP_DATA = " + json.dumps(payload) + ";\n", encoding="utf-8")


def write_svg(map_data: dict) -> None:
    size = 64
    pad = 110
    xs, ys = zip(*(pixel(h["q"], h["r"], size) for h in map_data["hexes"]))
    min_x, max_x = min(xs) - size - pad, max(xs) + size + pad
    min_y, max_y = min(ys) - size - pad, max(ys) + size + pad
    width, height = max_x - min_x, max_y - min_y
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="{min_x:.1f} {min_y:.1f} {width:.1f} {height:.1f}" width="{width:.0f}" height="{height:.0f}">',
        "<style>text{font-family:Helvetica,Arial,sans-serif;fill:#f6f1e3;paint-order:stroke;stroke:#140c08;stroke-width:3px;stroke-linejoin:round}</style>",
        f'<rect x="{min_x}" y="{min_y}" width="{width}" height="{height}" fill="#0b1020"/>',
    ]
    flat_w, flat_h = size * 2, size * math.sqrt(3)
    for h in map_data["hexes"]:
        cx, cy = pixel(h["q"], h["r"], size)
        pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in hex_corners(cx, cy, size))
        color = h["color"] or "#8aa0c8"
        clip = f"hex-{h['q']}-{h['r']}"
        parts.append(f'<clipPath id="{clip}"><polygon points="{pts}"/></clipPath>')
        parts.append(
            f'<image href="{h["image_url"]}" x="{cx - flat_w / 2:.2f}" y="{cy - flat_h / 2:.2f}" width="{flat_w:.2f}" height="{flat_h:.2f}" '
            f'transform="rotate({h["image_rotation"]} {cx:.2f} {cy:.2f})" clip-path="url(#{clip})" preserveAspectRatio="xMidYMid slice"/>'
        )
        parts.append(
            f'<polygon points="{pts}" fill="none" stroke="{color}" stroke-width="{6 if h["is_home"] or h["is_mecatol"] else 2.5}"/>'
        )
        label = h["position"] or ("Mecatol Rex" if h["is_mecatol"] else "")
        if label:
            parts.append(f'<text x="{cx:.2f}" y="{cy + size * 0.72:.2f}" text-anchor="middle" font-size="11">{label}</text>')
        parts.append(f'<text x="{cx:.2f}" y="{cy - size * 0.55:.2f}" text-anchor="middle" font-size="12">{h["tile_id"]}</text>')
    parts.append("</svg>")
    (DATA / "map.svg").write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    catalog = json.loads((DATA / "tiles.json").read_text(encoding="utf-8"))
    factions = json.loads((DATA / "factions.json").read_text(encoding="utf-8"))
    map_data = build(catalog, factions)
    ids = [h["tile_id"] for h in map_data["hexes"] if h["tile_id"] not in {"0", "18"}]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SystemExit(f"Duplicate tiles: {sorted(dupes)}")
    write_csv(map_data)
    write_json(map_data)
    write_svg(map_data)
    print(f"Wrote {len(map_data['hexes'])} hexes")
    print("TTS:", map_data["tts_map_string"])


if __name__ == "__main__":
    main()
