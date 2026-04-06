"""Function calling schemas for Arsitrad agent modules."""

# Each advisory module exposes tools with structured input/output
# These are registered with Gemma 4 function calling

TOOL_SCHEMAS = [
    {
        "name": "report_disaster_damage",
        "description": "Classify building damage from disaster and generate repair recommendations based on BNPB standards and SNI construction codes.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Disaster location (village, district, city, province)"
                },
                "disaster_type": {
                    "type": "string",
                    "enum": ["gempa", "banjir", "tsunami", "longsor", "puting_beliung", "kebakaran", "lainnya"],
                    "description": "Type of disaster"
                },
                "building_type": {
                    "type": "string",
                    "description": "Type of building (rumah_tinggal, gedung_perkantoran, sekolah, pasar, lainnya)"
                },
                "damage_description": {
                    "type": "string",
                    "description": "Detailed description of visible damage"
                },
                "photo_urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "URLs or paths to damage photos (optional)"
                }
            },
            "required": ["location", "disaster_type", "building_type", "damage_description"]
        }
    },
    {
        "name": "advise_settlement_upgrading",
        "description": "Generate prioritized upgrading recommendations for informal settlement areas based on Indonesian housing standards.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Settlement location"
                },
                "population_density": {
                    "type": "number",
                    "description": "Population density per hectare"
                },
                "current_infrastructure": {
                    "type": "string",
                    "description": "Description of existing infrastructure (roads, water, electricity, sanitation)"
                },
                "budget_constraint_idr": {
                    "type": "number",
                    "description": "Available budget in Indonesian Rupiah"
                },
                "priority_goals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Priority goals: meningkat_keselamatan, menambah_fasilitas_air, dll"
                }
            },
            "required": ["location", "population_density", "current_infrastructure", "budget_constraint_idr"]
        }
    },
    {
        "name": "navigate_building_permit",
        "description": "Walk through the Indonesian IMB (Izin Mendirikan Bangunan) application process with step-by-step guidance.",
        "parameters": {
            "type": "object",
            "properties": {
                "building_type": {
                    "type": "string",
                    "enum": ["rumah_tinggal", "apartemen", "gedung_komersial", "gedung_industri", "fasilitas_umum", "lainnya"],
                    "description": "Type of building"
                },
                "location": {
                    "type": "string",
                    "description": "Building location (city/district)"
                },
                "floor_area_m2": {
                    "type": "number",
                    "description": "Total floor area in square meters"
                },
                "building_height_m": {
                    "type": "number",
                    "description": "Building height in meters (if applicable)"
                },
                "land_area_m2": {
                    "type": "number",
                    "description": "Land area in square meters"
                },
                "building_function": {
                    "type": "string",
                    "description": "Building function: hunian, usaha, campuran"
                }
            },
            "required": ["building_type", "location", "floor_area_m2", "land_area_m2"]
        }
    },
    {
        "name": "advise_passive_cooling",
        "description": "Recommend passive cooling strategies for tropical Indonesian buildings based on thermal comfort standards.",
        "parameters": {
            "type": "object",
            "properties": {
                "building_dimensions": {
                    "type": "object",
                    "properties": {
                        "length_m": {"type": "number"},
                        "width_m": {"type": "number"},
                        "height_m": {"type": "number"},
                        "floor_count": {"type": "number"}
                    },
                    "required": ["length_m", "width_m", "height_m"]
                },
                "orientation": {
                    "type": "string",
                    "description": "Building main orientation (utara, selatan, timur, barat, atau derajat)"
                },
                "materials": {
                    "type": "object",
                    "properties": {
                        "wall_material": {"type": "string", "description": "Wall: bata, beton, kayu, dll"},
                        "roof_material": {"type": "string", "description": "Roof: genteng, metal, beton, dll"},
                        "window_type": {"type": "string", "description": "Windows: kayu_aluminium, UPVC, dll"}
                    }
                },
                "location_climate_zone": {
                    "type": "string",
                    "enum": ["dataran_rendah_pesisir", "dataran_tinggi", "kutub", "tropical_basah", "tropical_kering"],
                    "description": "Climate zone of building location"
                },
                "budget_constraint_idr": {
                    "type": "number",
                    "description": "Available budget for cooling improvements in IDR"
                }
            },
            "required": ["building_dimensions", "orientation", "materials", "location_climate_zone"]
        }
    },
    {
        "name": "lookup_regulation",
        "description": "Look up specific Indonesian building regulations, SNI standards, or construction codes.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query about building regulations"
                },
                "regulation_type": {
                    "type": "string",
                    "enum": ["sni", "uu", "pp", "permen", "perda", "all"],
                    "description": "Type of regulation to search"
                }
            },
            "required": ["query"]
        }
    }
]