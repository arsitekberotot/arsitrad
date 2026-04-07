# Local Regulations — 5 Islands, 15 Provinces

## Overview

Extends the national-level knowledge graph with provincial/local spatial and regulatory data across 5 major Indonesian islands.

## Coverage

| Island | Province | Special Focus |
|--------|---------|---------------|
| Java | DKI Jakarta | National capital, highest complexity |
| Java | Jawa Barat | Bandung basin seismic risk |
| Java | Jawa Timur | Surabaya industrial corridor |
| Sumatra | Sumatera Utara | Sumatran fault, high seismic |
| Sumatra | Sumatera Selatan | Musi floodplain, peat soil |
| Sumatra | Lampung | Sunda megathrust, tsunami risk |
| Kalimantan | Kalimantan Timur | IKN influence zone |
| Kalimantan | Kalimantan Selatan | Coal mining, Barito flood |
| Kalimantan | Kalimantan Barat | Kapuas floodplain |
| Sulawesi | Sulawesi Selatan | Sulawesi fault zone |
| Sulawesi | Sulawesi Utara | Volcanic, Ring of Fire |
| Sulawesi | Sulawesi Tengah | Post-2018 rebuilding, liquefaction |
| Papua | Papua | Special autonomy, very high seismic |
| Papua | Papua Barat | Mining/petroleum coastal |
| Papua | Papua Tengah | Remote highlands infrastructure |

## File Structure

```
local_regulations/
├── nodes/
│   ├── java_nodes.json      15 nodes (3 provinces x 5 nodes each)
│   ├── sumatra_nodes.json    15 nodes
│   ├── kalimantan_nodes.json  15 nodes
│   ├── sulawesi_nodes.json   15 nodes
│   └── papua_nodes.json      15 nodes
└── edges/
    ├── java_edges.json       intra-island edges
    ├── sumatra_edges.json
    ├── kalimantan_edges.json
    ├── sulawesi_edges.json
    ├── papua_edges.json
    └── cross_island_edges.json  8 edges bridging local -> national modules
```

## Node Types (Local)

| type | meaning |
|------|---------|
| `province_node` | Province-level metadata, special rules, seismic zone |
| `spatial_plan` | RDTR — zoning, FAR, height limits per municipality |
| `hazard_zone` | Seismic classification (KDS A-E per SNI 1726) |
| `risk_profile` | Multi-hazard: flood, tsunami, volcanic, landslide |
| `local_regulation_node` | Perda that supplements or overrides national |

## What You Need to Verify

Each node and edge has `"verified": false`. Your job:

1. Cross-check the seismic KDS zone assignment against BNPB/SNI 1726 maps
2. Verify disaster risk priorities per province against BNPB risk data
3. Confirm Perda numbers and years are correct
4. Verify RDTR names and dates
5. Check special rules (e.g., IKN proximity for Kalimantan Timur, liquefaction for Sulawesi Tengah)

## Key Cross-Module Intersections

| Cross-island Edge | What it connects |
|------------------|-----------------|
| E_CROSSISLAND_01 | Sulawesi Utara KDS D-E -> RETROFIT_GATE (disaster module) |
| E_CROSSISLAND_02 | Sumatera Utara KDS D-E -> RETROFIT_GATE |
| E_CROSSISLAND_03 | Papua KDS D-E -> RETROFIT_GATE |
| E_CROSSISLAND_04 | Sulawesi Tengah liquefaction -> FIRE_LIFT_GATE |
| E_CROSSISLAND_05 | DKI Jakarta RDTR -> PBG (permit module) |
| E_CROSSISLAND_07 | Sulawesi Tengah Perda -> SRPMK_GATE (stricter than SNI) |
| E_CROSSISLAND_08 | Lampung tsunami risk -> PBG |
