"""Disaster Damage Reporter Module — classifies building damage and generates repair recommendations."""

from typing import Dict, List, Optional
from .schema import TOOL_SCHEMAS


# BNPB Damage Classification Standards
DAMAGE_CLASSIFICATION = {
    "rusak_ringan": {
        "description": "Kerusakan struktur ringan, bangunan masih dapat dihuni",
        "indicators": [
            "Retak rambut pada dinding",
            "Kerusakan pada bagian non-struktur (plester, cat)",
            "Atap genteng pecah atau bergeser < 10%",
            "Jendela dan pintu tidak rata"
        ],
        "repair_priority": 3,
        "estimated_cost_per_m2_idr": 50000
    },
    "rusak_sedang": {
        "description": "Kerusakan struktur sedang, bangunan tidak aman dihuni sebelum diperbaiki",
        "indicators": [
            "Retak lebar pada dinding结构性",
            "Kerusakan pada kolom atau balok (tidak collapse)",
            "Atap genteng bergeser > 10%",
            "Lantai pecah atau tidak rata",
            "Pondasi mengalami penurunan tidak merata"
        ],
        "repair_priority": 2,
        "estimated_cost_per_m2_idr": 200000
    },
    "rusak_berat": {
        "description": "Kerusakan struktur berat atau collapse partial, bangunan tidak dapat diperbaiki",
        "indicators": [
            "Kolom atau balok utama patah atau kolaps",
            "Seluruh dinding结构性 retak parah",
            "Pondasi gagal/ambles",
            "Atap runtuh",
            "Bangunan miring > 5 derajat"
        ],
        "repair_priority": 1,
        "estimated_cost_per_m2_idr": 500000
    }
}


def classify_disaster_damage(disaster_type: str, damage_description: str) -> Dict:
    """Classify damage based on disaster type and description."""
    # Simple keyword-based classification
    # In production: integrate with fine-tuned Gemma 4 vision model

    damage_lower = damage_description.lower()

    if any(kw in damage_lower for kw in ["kolaps", "runtuh", "patah", "ambles", "miring", "seluruh", "parah"]):
        damage_key = "rusak_berat"
    elif any(kw in damage_lower for kw in ["retak", "geser", "pecah", "sedang", "tidak rata"]):
        damage_key = "rusak_sedang"
    else:
        damage_key = "rusak_ringan"

    return {
        "damage_key": damage_key,
        **DAMAGE_CLASSIFICATION[damage_key],
    }


def generate_repair_recommendations(
    damage_class: str,
    building_type: str,
    floor_area_m2: float,
    disaster_type: str
) -> Dict:
    """Generate prioritized repair recommendations."""
    damage_info = DAMAGE_CLASSIFICATION.get(damage_class, DAMAGE_CLASSIFICATION["rusak_ringan"])
    
    recommendations = []
    
    if damage_class == "rusak_ringan":
        recommendations = [
            {"step": 1, "action": "Perbaiki plesteran dan acian dinding", "estimated_cost_idr": 100000},
            {"step": 2, "action": "Cat ulang seluruh dinding", "estimated_cost_idr": 75000},
            {"step": 3, "action": "Penggantian genteng yang pecah", "estimated_cost_idr": 50000},
            {"step": 4, "action": "Perbaikan engsel pintu dan jendela", "estimated_cost_idr": 25000}
        ]
    elif damage_class == "rusak_sedang":
        recommendations = [
            {"step": 1, "action": "Evaluasi struktural oleh ahli sipil", "estimated_cost_idr": 500000},
            {"step": 2, "action": "Injeksi grout pada retak struktural", "estimated_cost_idr": 300000},
            {"step": 3, "action": "Pemasangan bracing sementara", "estimated_cost_idr": 200000},
            {"step": 4, "action": "Perbaikan/penggantian genteng > 10%", "estimated_cost_idr": 150000},
            {"step": 5, "action": "Perataan lantai dan perbaikan pondasi", "estimated_cost_idr": 400000}
        ]
    else:  # rusak_berat
        recommendations = [
            {"step": 1, "action": "EVALUASI TOTAL oleh tim ahli struktural", "estimated_cost_idr": 1000000},
            {"step": 2, "action": "Stabilisasi struktur sementara (jika memungkinkan)", "estimated_cost_idr": 500000},
            {"step": 3, "action": "Penawaran: perbaikan total vs demolisi + rebuild", "estimated_cost_idr": 0},
            {"step": 4, "action": "Pengawasan struktural selama perbaikan", "estimated_cost_idr": 750000}
        ]
    
    # Add disaster-specific recommendations
    if disaster_type == "gempa":
        recommendations.append({
            "step": len(recommendations) + 1,
            "action": "Evaluasi ketahanan gempa sesuai SNI 1726:2019",
            "estimated_cost_idr": 250000,
            "note": "Wajib untuk bangunan di zona gempa Indonesia"
        })
    
    total_estimate = sum(r.get("estimated_cost_idr", 0) for r in recommendations)
    
    return {
        "damage_classification": damage_class,
        "description": damage_info["description"],
        "repair_priority": damage_info["repair_priority"],
        "building_type": building_type,
        "floor_area_m2": floor_area_m2,
        "recommendations": recommendations,
        "total_estimated_cost_idr": total_estimate,
        "per_m2_cost_idr": damage_info["estimated_cost_per_m2_idr"],
        "sni_references": ["SNI 1726:2019", "SNI 2847:2019", "UU No. 28/2002"]
    }


class DisasterDamageReporter:
    """Main class for disaster damage reporting — integrates with RAG and Gemma 4."""
    
    def __init__(self, retriever=None, model=None):
        self.retriever = retriever
        self.model = model
    
    def report(
        self,
        location: str,
        disaster_type: str,
        building_type: str,
        damage_description: str,
        floor_area_m2: Optional[float] = None,
        photo_urls: Optional[List[str]] = None
    ) -> Dict:
        """Main reporting function — classify damage and generate recommendations."""
        # Step 1: Classify damage
        damage_info = classify_disaster_damage(disaster_type, damage_description)
        damage_key = str(damage_info.get("damage_key", "rusak_ringan"))

        # Step 2: Get area estimate if not provided
        if floor_area_m2 is None:
            floor_area_m2 = self._estimate_area(building_type)

        # Step 3: Generate repair recommendations
        report = generate_repair_recommendations(
            damage_key,
            building_type,
            floor_area_m2,
            disaster_type
        )
        
        # Step 4: Add location context from regulations
        if self.retriever:
            context, citations = self.retriever.retrieve_with_citation(
                f"Persyaratan bangunan tahan gempa {location}", top_k=3
            )
            report["location_regulations"] = context[:500]
            report["regulation_citations"] = citations
        
        # Step 5: Add disaster-specific context
        report["disaster_type"] = disaster_type
        report["location"] = location
        report["building_type"] = building_type
        report["photo_urls"] = photo_urls or []
        
        return report
    
    def _estimate_area(self, building_type: str) -> float:
        """Estimate floor area based on building type (rough defaults)."""
        defaults = {
            "rumah_tinggal": 60.0,
            "gedung_perkantoran": 500.0,
            "sekolah": 300.0,
            "pasar": 200.0,
            "lainnya": 100.0
        }
        return defaults.get(building_type, 100.0)
    
    def format_report(self, report: Dict) -> str:
        """Format report as readable text."""
        lines = [
            f"=== LAPORAN KERUSAKAN BANGUNAN ===",
            f"Lokasi: {report.get('location', 'N/A')}",
            f"Tipe Bencana: {report.get('disaster_type', 'N/A').upper()}",
            f"Tipe Bangunan: {report.get('building_type', 'N/A')}",
            f"",
            f"KLASIFIKASI KERUSAKAN: {report.get('damage_classification', 'N/A').upper()}",
            f"Deskripsi: {report.get('description', 'N/A')}",
            f"Prioritas Perbaikan: {report.get('repair_priority', 'N/A')}",
            f"",
            f"ESTIMASI BIAYA:",
            f"Per m2: Rp {report.get('per_m2_cost_idr', 0):,.0f}",
            f"Total Estimasi: Rp {report.get('total_estimated_cost_idr', 0):,.0f}",
            f"",
            f"REKOMENDASI PERBAIKAN:"
        ]
        
        for rec in report.get("recommendations", []):
            lines.append(f"  Step {rec['step']}: {rec['action']}")
            if rec.get("estimated_cost_idr"):
                lines.append(f"    Estimasi: Rp {rec['estimated_cost_idr']:,.0f}")
            if rec.get("note"):
                lines.append(f"    Catatan: {rec['note']}")
        
        if report.get("sni_references"):
            lines.append(f"")
            lines.append(f"REFERENSI SNI:")
            for ref in report["sni_references"]:
                lines.append(f"  - {ref}")
        
        return "\n".join(lines)