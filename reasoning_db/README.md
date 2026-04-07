# Arsitrad Reasoning Database

Lightweight knowledge graph for regulatory + physics + procedural reasoning.
Built with JSON + NetworkX. Ships with the app — no external DB needed.

## Structure

```
reasoning_db/
├── nodes/
│   ├── disaster_nodes.json             7 nodes  ✓ 7/7
│   ├── permit_nodes.json              10 nodes ✓ 10/10
│   ├── settlement_nodes.json           7 nodes ✓ 7/7
│   ├── cooling_nodes.json              8 nodes ✓ 8/8
│   └── local_regulations_nodes.json   24 nodes ✓ 24/24
└── edges/
    ├── disaster_edges.json             6 edges ✓ 6/6
    ├── permit_edges.json               9 edges ✓ 9/9
    ├── settlement_edges.json           6 edges ✓ 6/6
    ├── cooling_edges.json              7 edges ✓ 7/7
    ├── local_regulations_edges.json   20 edges ✓ 20/20
    └── cross_module_edges.json         5 edges ✓ 5/5
```

**56 nodes · 53 edges · 5 modules · ALL VERIFIED ✓**

## Modules

| Module | Nodes | Type |
|--------|-------|------|
| disaster | 7 | Seismic KDS, SRPMK, retrofit, fire lift |
| permit | 10 | NIB→KKPR→PBG→SLF pipeline, accessibility, BIM |
| settlement | 7 | MBR housing, PSU standards, spatial ratios, PPPSRS |
| cooling | 8 | OTTV, IKE, WWR heat gain, BGH targets |
| local_regulations | 24 | City-specific KDB/KDH/KLB per municipality |

## Local Regulations Coverage (24 nodes, 20 edges)

Cities: Jakarta, Bandung, Semarang, Surakarta, Malang (Jawa) · Balikpapan, Pontianak (Kalimantan) · Padang, Medan (Sumatera)

Key city-specific thresholds:
- Jakarta: KDB/KDH zone-based; >8 lantai = bangunan tinggi
- Bandung: KDB tiered (>60%/45-60%/<45%); KDH min 10%
- Semarang: KDH min 20%
- Surakarta: KDB max 85%; KDH min 10%; KLB max 360% dari KDB
- Malang: KDB density-based (renggang 40-50%, sedang 50-60%, padat 60-70%)
- Medan: KLB max 80%; max 50 lantai
- Balikpapan/Pontianak/Padang: >8 lantai = bangunan tinggi

## Node types

| type | meaning |
|------|---------|
| `regulation` | A specific law/standard/SNI |
| `procedural_gate` | A step that must pass before proceeding |
| `terminal_reject` | A dead-end |
| `physics_rule` | A technical calculation or formula |
| `structural_gate` | Engineering safety threshold |
| `retrofit_gate` | Assessment outcome gate |
| `fire_gate` | Fire safety requirement |
| `technical_gate` | Technical compliance threshold |
| `eligibility_gate` | User/profile qualification check |
| `cross_module_node` | Bridges multiple modules |

## Edge types

| type | meaning |
|------|---------|
| `SEQUENCES` | Must happen in this order |
| `GATES` | Conditional threshold — pass or fail |
| `CONDITIONAL_TRIGGERS` | Activates when condition is met |
| `DEFINES` | Regulation establishes this node |
| `CROSS_MODULE_BRIDGE` | Connects logic across modules |
| `CONTRIBUTES_TO` | Helps satisfy a target |
| `REFERENCES` | Cross-references but doesn't gate |
| `COMBINES_WITH` | Physics/load combination |
| `ADDS_REQUIREMENT` | Layers additional requirements |
| `PROCEDURAL_NEXT` | Next step in a procedure |
| `COEXISTS_WITH` | Must coexist simultaneously |
