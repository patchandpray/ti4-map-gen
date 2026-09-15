#!/usr/bin/env python3
"""Build Operation Clever Knowledge map CSV, JSON, and SVG from local draft picks."""

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
    "id": "20260630_f19cd238308d0d7a",
    "name": "Operation Clever Knowledge",
    "source": "https://milty.shenanigans.be/d/20260630_f19cd238308d0d7a?fresh=1#map",
    "seed": 240839053603649,
    "mecatol": "112",
    "notes": "Faction, slice, and seat picks were filled locally; the live milty draft may still be incomplete.",
}

# 1-based slice numbers as shown on milty, each 5 tiles in milty slot order 0-4.
SLICES = {
    1: ["36", "26", "104", "77", "116"],
    2: ["22", "109", "114", "97", "68"],
    3: ["100", "64", "80", "69", "43"],
    4: ["108", "34", "21", "115", "48"],
    5: ["20", "72", "44", "106", "113"],
    6: ["24", "76", "42", "38", "79"],
    7: ["103", "74", "63", "117", "40"],
}

SLICE_SLOT_NAMES = {
    "0": "left of home",
    "1": "in front of home",
    "2": "right of home",
    "3": "left-front (shared)",
    "4": "inner (Mecatol-adjacent)",
    "H": "home system",
    "M": "Mecatol Rex",
}

PLAYERS = [
    {
        "position": 0,
        "seat": "Speaker",
        "name": "Rens",
        "faction": "Last Bastion",
        "slice": 4,
        "color": "#e67e22",
    },
    {
        "position": 1,
        "seat": "2nd",
        "name": "Tim",
        "faction": "The Yssaril Tribes",
        "slice": 7,
        "color": "#2ecc71",
    },
    {
        "position": 2,
        "seat": "3rd",
        "name": "Jochem",
        "also_known_as": "Arie",
        "faction": "The Ghosts of Creuss",
        "slice": 1,
        "color": "#5dade2",
    },
    {
        "position": 3,
        "seat": "4th",
        "name": "Sander",
        "faction": "The Titans of Ul",
        "slice": 2,
        "color": "#e84393",
    },
    {
        "position": 4,
        "seat": "5th",
        "name": "Paul",
        "faction": "The Empyrean",
        "slice": 3,
        "color": "#9b59b6",
    },
    {
        "position": 5,
        "seat": "6th",
        "name": "Ruben",
        "faction": "The Barony of Letnev",
        "slice": 6,
        "color": "#f1c40f",
    },
]

UNUSED_FACTIONS = [
    "The Ral Nel Consortium",
    "The Arborec",
    "The Deepwrought Scholarate",
]
UNUSED_SLICE = 5

# Axial (q, r, code) from miltydraft MAP_6. Speaker is north.
MAP_6 = [
    (0, -3, "0-H"),
    (1, -3, "0-0"),
    (2, -3, "1-2"),
    (3, -3, "1-H"),
    (-1, -2, "0-2"),
    (0, -2, "0-1"),
    (1, -2, "0-3"),
    (2, -2, "1-1"),
    (3, -2, "1-0"),
    (-2, -1, "5-0"),
    (-1, -1, "5-3"),
    (0, -1, "0-4"),
    (1, -1, "1-4"),
    (2, -1, "1-3"),
    (3, -1, "2-2"),
    (-3, 0, "5-H"),
    (-2, 0, "5-1"),
    (-1, 0, "5-4"),
    (0, 0, "M"),
    (1, 0, "2-4"),
    (2, 0, "2-1"),
    (3, 0, "2-H"),
    (-3, 1, "5-2"),
    (-2, 1, "4-3"),
    (-1, 1, "4-4"),
    (0, 1, "3-4"),
    (1, 1, "2-3"),
    (2, 1, "2-0"),
    (-3, 2, "4-0"),
    (-2, 2, "4-1"),
    (-1, 2, "3-3"),
    (0, 2, "3-1"),
    (1, 2, "3-2"),
    (-3, 3, "4-H"),
    (-2, 3, "4-2"),
    (-1, 3, "3-0"),
    (0, 3, "3-H"),
]

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
    x = size * (3 / 2 * q)
    y = size * (math.sqrt(3) / 2 * q + math.sqrt(3) * r)
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
        stations.append(
            {
                "name": station.get("name"),
                "resources": res,
                "influence": inf,
            }
        )
    label_parts = [p["name"] for p in planets] + [s["name"] for s in stations]
    if not label_parts:
        if raw.get("anomaly"):
            label_parts = [str(raw["anomaly"])]
        elif raw.get("wormhole"):
            label_parts = [f"{raw['wormhole']} wormhole"]
        else:
            label_parts = ["Empty space"]
    return {
        "tile_id": str(tile_id),
        "type": raw.get("type"),
        "set": raw.get("set"),
        "wormhole": raw.get("wormhole"),
        "anomaly": raw.get("anomaly"),
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


def slice_summary(slice_no: int, catalog: dict) -> dict:
    tiles = [summarize_tile(tid, catalog) for tid in SLICES[slice_no]]
    return {
        "slice": slice_no,
        "tiles": SLICES[slice_no],
        "resources": sum(t["resources"] for t in tiles),
        "influence": sum(t["influence"] for t in tiles),
        "optimal_resources": sum(t["optimal_resources"] for t in tiles),
        "optimal_influence": sum(t["optimal_influence"] for t in tiles),
        "specialties": [s for t in tiles for s in t["specialties"]],
        "wormholes": [t["wormhole"] for t in tiles if t["wormhole"]],
        "anomalies": [t["anomaly"] for t in tiles if t["anomaly"]],
        "systems": tiles,
    }


def build(catalog: dict, factions: dict) -> dict:
    by_pos = {p["position"]: p for p in PLAYERS}
    hexes = []
    for q, r, code in MAP_6:
        if code == "M":
            summary = summarize_tile(DRAFT["mecatol"], catalog)
            hexes.append(
                {
                    **summary,
                    "q": q,
                    "r": r,
                    "s": -q - r,
                    "ring": cube_ring(q, r),
                    "map_code": code,
                    "slice_slot": "M",
                    "slot_name": SLICE_SLOT_NAMES["M"],
                    "is_home": False,
                    "is_mecatol": True,
                    "player": None,
                    "seat": None,
                    "faction": None,
                    "slice": None,
                }
            )
            continue
        pos, slot = code.split("-")
        pos = int(pos)
        player = by_pos[pos]
        if slot == "H":
            tile_id = factions[player["faction"]]["homesystem"]
        else:
            tile_id = SLICES[player["slice"]][int(slot)]
        summary = summarize_tile(tile_id, catalog)
        hexes.append(
            {
                **summary,
                "q": q,
                "r": r,
                "s": -q - r,
                "ring": cube_ring(q, r),
                "map_code": code,
                "slice_slot": slot,
                "slot_name": SLICE_SLOT_NAMES[slot],
                "is_home": slot == "H",
                "is_mecatol": False,
                "player": player["name"],
                "seat": player["seat"],
                "faction": player["faction"],
                "slice": player["slice"],
            }
        )

    coord_index = {(h["q"], h["r"]): i for i, h in enumerate(hexes)}
    tts_coords = []
    for radius in range(1, 4):
        tts_coords.extend(axial_ring(radius))
    tts_tiles = [DRAFT["mecatol"]]
    for q, r in tts_coords:
        idx = coord_index.get((q, r))
        tts_tiles.append(hexes[idx]["tile_id"] if idx is not None else "0")
    for i, h in enumerate(hexes):
        h["tts_index"] = None
    hexes[coord_index[(0, 0)]]["tts_index"] = 0
    for i, (q, r) in enumerate(tts_coords, start=1):
        if (q, r) in coord_index:
            hexes[coord_index[(q, r)]]["tts_index"] = i

    players_out = []
    for player in PLAYERS:
        faction = factions[player["faction"]]
        players_out.append(
            {
                **player,
                "faction_id": faction["id"],
                "homesystem": faction["homesystem"],
                "wiki": faction["wiki"],
                "reference_url": REFERENCE_IMG.format(id=faction["id"]),
                "icon_url": FACTION_IMG.format(id=faction["id"]),
                "slice_summary": slice_summary(player["slice"], catalog),
            }
        )

    unused_factions = []
    for name in UNUSED_FACTIONS:
        faction = factions[name]
        unused_factions.append(
            {
                "name": name,
                "faction_id": faction["id"],
                "wiki": faction["wiki"],
                "homesystem": faction["homesystem"],
                "icon_url": FACTION_IMG.format(id=faction["id"]),
                "reference_url": REFERENCE_IMG.format(id=faction["id"]),
            }
        )

    return {
        "draft": DRAFT,
        "players": players_out,
        "hexes": hexes,
        "tts_map_string": " ".join(tts_tiles),
        "unused_slice": slice_summary(UNUSED_SLICE, catalog),
        "unused_factions": unused_factions,
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
        "player",
        "seat",
        "faction",
        "slice",
        "slice_slot",
        "slot_name",
        "map_code",
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
                    "tts_index": h["tts_index"],
                    "q": h["q"],
                    "r": h["r"],
                    "s": h["s"],
                    "ring": h["ring"],
                    "tile_id": h["tile_id"],
                    "system_label": h["system_label"],
                    "planets": "; ".join(
                        f"{p['name']} {p['resources']}/{p['influence']}"
                        + (f" {p['trait']}" if p["trait"] else "")
                        + (" legendary" if p["legendary"] else "")
                        + (f" tech:{','.join(p['specialties'])}" if p["specialties"] else "")
                        for p in h["planets"]
                    ),
                    "stations": "; ".join(
                        f"{s['name']} {s['resources']}/{s['influence']}" for s in h["stations"]
                    ),
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
                    "player": h["player"] or "",
                    "seat": h["seat"] or "",
                    "faction": h["faction"] or "",
                    "slice": h["slice"] if h["slice"] is not None else "",
                    "slice_slot": h["slice_slot"],
                    "slot_name": h["slot_name"],
                    "map_code": h["map_code"],
                    "image_url": h["image_url"],
                }
            )
    (DATA / "tts-map-string.txt").write_text(map_data["tts_map_string"] + "\n", encoding="utf-8")


def write_json(map_data: dict) -> None:
    (DATA / "map.json").write_text(json.dumps(map_data, indent=2) + "\n", encoding="utf-8")
    (DATA / "map.js").write_text(
        "window.MAP_DATA = " + json.dumps(map_data) + ";\n",
        encoding="utf-8",
    )


def write_svg(map_data: dict) -> None:
    size = 64
    pad = 90
    xs, ys = zip(*(pixel(h["q"], h["r"], size) for h in map_data["hexes"]))
    min_x, max_x = min(xs) - size - pad, max(xs) + size + pad
    min_y, max_y = min(ys) - size - pad, max(ys) + size + pad
    width, height = max_x - min_x, max_y - min_y
    player_color = {p["name"]: p["color"] for p in map_data["players"]}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="{min_x:.1f} {min_y:.1f} {width:.1f} {height:.1f}" width="{width:.0f}" height="{height:.0f}">',
        "<style>text{font-family:Helvetica,Arial,sans-serif;fill:#f6f1e3;paint-order:stroke;stroke:#140c08;stroke-width:3px;stroke-linejoin:round}</style>",
        f'<rect x="{min_x}" y="{min_y}" width="{width}" height="{height}" fill="#0b1020"/>',
    ]
    for h in map_data["hexes"]:
        cx, cy = pixel(h["q"], h["r"], size)
        pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in hex_corners(cx, cy, size))
        color = player_color.get(h["player"], "#f4d03f") if not h["is_mecatol"] else "#f4d03f"
        clip = f"hex-{h['q']}-{h['r']}"
        parts.append(f'<clipPath id="{clip}"><polygon points="{pts}"/></clipPath>')
        parts.append(
            f'<image href="{h["image_url"]}" x="{cx-size:.2f}" y="{cy-size:.2f}" width="{size*2}" height="{size*2}" clip-path="url(#{clip})" preserveAspectRatio="xMidYMid slice"/>'
        )
        parts.append(
            f'<polygon points="{pts}" fill="none" stroke="{color}" stroke-width="{6 if h["is_home"] or h["is_mecatol"] else 2.5}"/>'
        )
        label = h["player"] if h["is_home"] else (h["system_label"][:18] if not h["is_mecatol"] else "Mecatol Rex")
        parts.append(
            f'<text x="{cx:.2f}" y="{cy+size*0.72:.2f}" text-anchor="middle" font-size="11">{label}</text>'
        )
        parts.append(
            f'<text x="{cx:.2f}" y="{cy-size*0.62:.2f}" text-anchor="middle" font-size="10">{h["tile_id"]}</text>'
        )
    parts.append("</svg>")
    (DATA / "map.svg").write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    catalog = json.loads((DATA / "tiles.json").read_text(encoding="utf-8"))
    factions = json.loads((DATA / "factions.json").read_text(encoding="utf-8"))
    map_data = build(catalog, factions)
    write_csv(map_data)
    write_json(map_data)
    write_svg(map_data)
    print(f"Wrote {len(map_data['hexes'])} hexes")
    print("TTS:", map_data["tts_map_string"])


if __name__ == "__main__":
    main()
