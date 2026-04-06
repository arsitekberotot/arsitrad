"""Passive Cooling Advisor — recommends tropical passive cooling strategies for Indonesian buildings."""

from typing import Dict, Optional


# Indonesian climate zones and thermal properties
CLIMATE_ZONES = {
    "dataran_rendah_pesisir": {
        "description": "Coastal lowlands — high humidity, moderate temperature variation",
        "avg_temp_c": 27-32,
        "humidity_pct": 70-90,
        "solar_radiation": "high",
        "passive_priority": ["cross_ventilation", "thermal_mass", "shading"]
    },
    "dataran_tinggi": {
        "description": "Highland areas — cooler, lower humidity",
        "avg_temp_c": 22-28,
        "humidity_pct": 60-80,
        "solar_radiation": "moderate-high",
        "passive_priority": ["orientation", "insulation", "natural_light"]
    },
    "tropical_basah": {
        "description": "Wet tropical — high rainfall, very high humidity",
        "avg_temp_c": 26-32,
        "humidity_pct": 80-100,
        "solar_radiation": "moderate",
        "passive_priority": ["cross_ventilation", "rain_screen", "moisture_management"]
    },
    "tropical_kering": {
        "description": "Dry tropical — low rainfall, high temperature variation",
        "avg_temp_c": 25-35,
        "humidity_pct": 30-60,
        "solar_radiation": "very_high",
        "passive_priority": ["thermal_mass", "shading", "evaporative_cooling"]
    }
}


# Material thermal properties
MATERIAL_PROPERTIES = {
    "wall": {
        "bata": {"conductivity": 0.45, "thermal_mass": "high", "description": "Bata merah — good thermal mass"},
        "beton": {"conductivity": 1.70, "thermal_mass": "very_high", "description": "Beton cor — high thermal mass, absorbs heat"},
        "kayu": {"conductivity": 0.14, "thermal_mass": "low", "description": "Kayu — good insulation, low thermal mass"},
        "batako": {"conductivity": 0.35, "thermal_mass": "medium", "description": "Batako — medium performance"},
        "hebel": {"conductivity": 0.11, "thermal_mass": "medium", "description": "Beton ringan (Hebel) — good insulation"}
    },
    "roof": {
        "genteng": {"conductivity": 0.55, "thermal_mass": "medium", "description": "Genteng tanah liat"},
        "metal": {"conductivity": 55.0, "thermal_mass": "low", "description": "Atap metal — absorbss heat significantly, needs insulation"},
        "beton": {"conductivity": 1.70, "thermal_mass": "very_high", "description": "Atap beton datar"}
    }
}


def calculate_thermal_performance(
    dimensions: Dict,
    orientation: str,
    materials: Dict,
    climate_zone: str
) -> Dict:
    """Calculate building thermal performance."""
    zone = CLIMATE_ZONES.get(climate_zone, CLIMATE_ZONES["dataran_rendah_pesisir"])
    
    volume = dimensions["length_m"] * dimensions["width_m"] * dimensions["height_m"]
    wall_area = 2 * (dimensions["length_m"] + dimensions["width_m"]) * dimensions["height_m"]
    
    # Simple U-value estimate
    wall_mat = MATERIAL_PROPERTIES["wall"].get(materials.get("wall_material", "bata"))
    roof_mat = MATERIAL_PROPERTIES["roof"].get(materials.get("roof_material", "genteng"))
    
    return {
        "volume_m3": volume,
        "wall_area_m2": wall_area,
        "climate_zone": climate_zone,
        "climate_description": zone["description"],
        "wall_material": wall_mat,
        "roof_material": roof_mat,
        "orientation": orientation
    }


def recommend_passive_cooling(
    dimensions: Dict,
    orientation: str,
    materials: Dict,
    climate_zone: str,
    budget_idr: Optional[float] = None
) -> Dict:
    """Generate passive cooling recommendations."""
    perf = calculate_thermal_performance(dimensions, orientation, materials, climate_zone)
    zone = CLIMATE_ZONES.get(climate_zone)
    
    recommendations = []
    
    # 1. Cross Ventilation (always recommended for Indonesia)
    recommendations.append({
        "category": "cross_ventilation",
        "title": "Cross Ventilation",
        "description": "Rancang openings pada sisi yang berhadapan untuk sirkulasi udara silang",
        "implementation": [
            "Tempatkan bukaan (jendela/pintu) pada minimal 2 sisi yang berhadapan",
            f"Ukuran bukaan minimum 20% dari luas dinding untuk aliran udara optimal",
            "Gunakan jendela yang dapat dibuka penuh (bukan kaca mati)",
            "Tambahkan ventilasi tinggi (ventilasiator) di bawah atap untuk exhaust udara panas",
            "Hindari penempatan furniture yang blocking aliran udara"
        ],
        "estimated_cost_idr": 500000,
        "thermal_impact": "8/10",
        "priority": "HIGH"
    })
    
    # 2. Shading (especially for west-facing)
    recommendations.append({
        "category": "shading",
        "title": "External Shading Devices",
        "description": "Pasang shading pada sisi yang exposed ke matahari langsung",
        "implementation": [
            "Overstek/atap menjorok: 0.8-1.2m untuk blocking sinar matahari tinggi",
            "Vertical fin pada sisi barat dan timur",
            "Planting pohon deciduous di sisi selatan dan barat",
            "Use reflective or light-colored exterior surfaces"
        ],
        "estimated_cost_idr": 2000000 if not budget_idr or budget_idr >= 2000000 else 0,
        "thermal_impact": "9/10",
        "priority": "HIGH"
    })
    
    # 3. Thermal Mass (for roofs especially)
    if materials.get("roof_material") == "metal":
        recommendations.append({
            "category": "thermal_mass",
            "title": "Roof Insulation Upgrade",
            "description": "Metal roof memiliki thermal conductivity tinggi — panas cepat masuk",
            "implementation": [
                "Tambahkan insulasi foil di bawah atap metal (sisi dalam)",
                "Atau gunakan cat reflective/insulasi pada atap metal",
                "Consider hybrid: metal roof dengan langitan (secondary ceiling)"
            ],
            "estimated_cost_idr": 1500000,
            "thermal_impact": "7/10",
            "priority": "HIGH"
        })
    else:
        recommendations.append({
            "category": "thermal_mass",
            "title": "Optimalisasi Thermal Mass Dinding",
            "description": "Dinding dengan thermal mass tinggi dapat absorbs panas siang dan release malam",
            "implementation": [
                "Pastikan dinding tidak langsung terekspos sinar matahari (shading above)",
                "Warna dinding luar: terang/reflektif",
                "Tambahkan ventilated air gap antara insulasi dan exterior wall"
            ],
            "estimated_cost_idr": 0,
            "thermal_impact": "6/10",
            "priority": "MEDIUM"
        })
    
    # 4. Evaporative Cooling (for dry zones)
    if climate_zone == "tropical_kering":
        recommendations.append({
            "category": "evaporative",
            "title": "Evaporative Cooling",
            "description": "Water features atau tanaman air untuk menurunkan suhu sekitar",
            "implementation": [
                "Tambahkan kolam/waduk kecil di area outdoor",
                "Vertical garden pada dinding yang facing matahari",
                "Sistem misting pada terrace/veranda",
                "Fountain dalam courtyard"
            ],
            "estimated_cost_idr": 3000000,
            "thermal_impact": "7/10",
            "priority": "MEDIUM"
        })
    
    # 5. Orientation optimization
    recommendations.append({
        "category": "orientation",
        "title": "Orientation Optimization",
        "description": f"Sisi {orientation} memiliki exposure thermal tertinggi",
        "implementation": [
            f"Minimize bukaan pada sisi {orientation}",
            "Place service spaces (WC, storage) pada sisi {orientation}",
            "Maximize bukaan pada sisi utara-selatan (untuk Indonesia)",
            "Consider rotating building mass untuk optimize solar access"
        ],
        "estimated_cost_idr": 0,
        "thermal_impact": "5/10",
        "priority": "MEDIUM"
    })
    
    # Filter by budget if provided
    if budget_idr:
        recommendations = [r for r in recommendations if r["estimated_cost_idr"] <= budget_idr]
    
    # Calculate estimated temperature reduction
    total_thermal_impact = sum(int(r["thermal_impact"].split("/")[0]) for r in recommendations)
    estimated_temp_reduction_c = min(total_thermal_impact * 0.5, 5.0)
    
    return {
        "building_dimensions": dimensions,
        "orientation": orientation,
        "climate_zone": climate_zone,
        "climate_description": zone.get("description", ""),
        "materials": materials,
        "thermal_performance": perf,
        "recommendations": recommendations,
        "total_recommendations": len(recommendations),
        "estimated_temp_reduction_c": round(estimated_temp_reduction_c, 1),
        "estimated_cooling_cost_idr": sum(r["estimated_cost_idr"] for r in recommendations),
        "sni_references": ["SNI 03-6572-2001", "SNI 03-6389-2000", "Pedoman Teknis Penghematan Energi"]
    }


class PassiveCoolingAdvisor:
    """Main class for passive cooling advice."""
    
    def __init__(self, retriever=None, model=None):
        self.retriever = retriever
        self.model = model
    
    def advise(
        self,
        dimensions: Dict,
        orientation: str,
        materials: Dict,
        climate_zone: str,
        budget_idr: Optional[float] = None
    ) -> Dict:
        """Generate cooling recommendations."""
        return recommend_passive_cooling(dimensions, orientation, materials, climate_zone, budget_idr)
    
    def format_advice(self, advice: Dict) -> str:
        """Format advice as readable text."""
        lines = [
            f"=== ANALISIS PENINGKATAN KENYAMANAN TERMAL ===",
            f"Ukuran Bangunan: {advice['building_dimensions']['length_m']}m x {advice['building_dimensions']['width_m']}m x {advice['building_dimensions']['height_m']}m",
            f"Orientation: {advice['orientation']}",
            f"Zona Iklim: {advice['climate_zone'].replace('_', ' ').title()}",
            f"  {advice['climate_description']}",
            f"",
            f"ESTIMASI PENURUNAN SUHU: {advice['estimated_temp_reduction_c']}°C (dengan semua rekomendasi)",
            f"TOTAL BIAYA IMPLEMENTASI: Rp {advice['estimated_cooling_cost_idr']:,.0f}",
            f"",
            f"REKOMENDASI:"
        ]
        
        for rec in advice["recommendations"]:
            lines.append(f"  [{rec['priority']}] {rec['title']}")
            lines.append(f"    {rec['description']}")
            lines.append(f"    Dampak termal: {rec['thermal_impact']}")
            if rec["estimated_cost_idr"] > 0:
                lines.append(f"    Estimasi biaya: Rp {rec['estimated_cost_idr']:,.0f}")
            else:
                lines.append(f"    Estimasi biaya: GRATIS (design adjustment)")
            lines.append(f"    Implementasi:")
            for impl in rec["implementation"]:
                lines.append(f"      - {impl}")
        
        lines.extend([
            f"",
            f"REFERENSI SNI:",
            *[f"  - {ref}" for ref in advice.get("sni_references", [])]
        ])
        
        return "\n".join(lines)