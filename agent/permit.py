"""Building Permit (IMB) Navigator — guides through Indonesian IMB application process."""

from typing import Dict, List, Optional


# IMB Process Steps (simplified — varies by daerah)
IMB_STEPS = [
    {
        "step": 1,
        "name": "Persiapan Berkas",
        "description": "Mempersiapkan seluruh berkas yang diperlukan",
        "required_docs": [
            "FC KTP pemohon (3 lembar)",
            "FC Sertifikat tanah (3 lembar)",
            "FC PBB последний 5 tahun",
            "Surat pernyataan kepemilikan tanah",
            "Denah lokasi (sitasi) skala 1:100",
            "Desain arsitektur (denah, tampakan, potongan) skala 1:100"
        ],
        "estimated_days": "7-14 hari",
        "estimated_cost_idr": 500000
    },
    {
        "step": 2,
        "name": "Konsultasi Teknis",
        "description": "Konsultasi dengan Dinas PUTR setempat untuk persetujuan prasarana",
        "required_docs": [
            "Formulir konsultasi teknis",
            "Denah lokasi",
            "Desain arsitektur awal"
        ],
        "estimated_days": "7 hari",
        "estimated_cost_idr": 0,
        "note": "Gratis, tapi perlu jadwalkan pertemuan"
    },
    {
        "step": 3,
        "name": "Pengajuan Permohonan IMB",
        "description": "Mengajukan permohonan IMB ke Dinas Pekerjaan Umum dan Tata Ruang",
        "required_docs": [
            "Formulir permohonan IMB (terbit)",
            "Berkas step 1 + 2",
            "Surat kuasa (jika dikuasakan)",
            "Bukti pembayaran retribusi"
        ],
        "estimated_days": "1 hari",
        "estimated_cost_idr": 1500000,
        "note": "Retribusi dihitung berdasarkan luas lantai dan fungsi bangunan"
    },
    {
        "step": 4,
        "name": "Pemeriksaan Lapangan",
        "description": "Tim dari Dinas melakukan pemeriksaan lokasi dan desain",
        "required_docs": [
            "Patok tanah (batas tanah)",
            "Gambar desain yang disetujui",
            "Rencana anggaran biaya (RAB)"
        ],
        "estimated_days": "14-30 hari",
        "estimated_cost_idr": 0
    },
    {
        "step": 5,
        "name": "Penerbitan IMB",
        "description": "Penerbitan izin setelah desain dan lokasi disetujui",
        "required_docs": [
            "Surat persetujuan teknis dari instansi terkait",
            "Berita acara pemeriksaan lapangan"
        ],
        "estimated_days": "7-14 hari",
        "estimated_cost_idr": 0
    }
]


def calculate_retribution(building_type: str, floor_area_m2: float, building_function: str) -> Dict:
    """Calculate IMB retribusi based on Perda-province templates."""
    # Simplified calculation — actual varies by daerah
    base_rates = {
        "rumah_tinggal": 15000,  # per m2
        "apartemen": 20000,
        "gedung_komersial": 25000,
        "gedung_industri": 22000,
        "fasilitas_umum": 10000,
        "lainnya": 18000
    }
    
    rate = base_rates.get(building_type, 18000)
    base_cost = floor_area_m2 * rate
    
    # Height multiplier for high-rise buildings
    height_factor = 1.0  # Simplified
    
    total = base_cost * height_factor
    
    return {
        "rate_per_m2_idr": rate,
        "floor_area_m2": floor_area_m2,
        "height_factor": height_factor,
        "total_retribution_idr": round(total, -3),  # Round to nearest 1000
        "breakdown": f"{floor_area_m2} m2 x Rp {rate:,}/m2 = Rp {base_cost:,.0f}"
    }


def get_imb_checklist(
    building_type: str,
    location: str,
    floor_area_m2: float,
    building_height_m: Optional[float] = None,
    land_area_m2: float = 0,
    building_function: str = "hunian"
) -> Dict:
    """Generate complete IMB checklist for a building project."""
    
    retribution = calculate_retribution(building_type, floor_area_m2, building_function)
    
    # Generate checklist items for each step
    all_checklist_items = []
    for step in IMB_STEPS:
        for doc in step["required_docs"]:
            all_checklist_items.append({
                "step": step["step"],
                "step_name": step["name"],
                "document": doc,
                "status": "pending"
            })
    
    total_cost = sum(step["estimated_cost_idr"] for step in IMB_STEPS) + retribution["total_retribution_idr"]
    
    # Add function-specific requirements
    additional_requirements = []
    if building_function == "usaha":
        additional_requirements.append("Persetujuan dari Dinas Perindustrian dan Perdagangan")
        additional_requirements.append("Dokumen AMDAL/UPL/UKL-UPL (jika required)")
    if floor_area_m2 > 500:
        additional_requirements.append("Dokumen Perencanaan Teknis Arsitektur bersertifikat")
        additional_requirements.append("Struktur企核算 dari engineer bersertifikat")
    if building_height_m and building_height_m > 8:
        additional_requirements.append("Persetujuan dari Dinas Pertamanan dan Pemakaman")
        additional_requirements.append("Analisa dampak lalu lintas (jika required)")
    
    return {
        "building_type": building_type,
        "location": location,
        "floor_area_m2": floor_area_m2,
        "land_area_m2": land_area_m2,
        "building_height_m": building_height_m,
        "building_function": building_function,
        "imb_steps": IMB_STEPS,
        "total_steps": len(IMB_STEPS),
        "estimated_total_days": sum([14, 7, 1, 30, 14]),  # max estimates
        "retribution": retribution,
        "estimated_total_cost_idr": total_cost,
        "checklist": all_checklist_items,
        "additional_requirements": additional_requirements,
        "sni_references": ["SNI 2847:2019", "SNI 1726:2019", "UU No. 28/2002", "PP No. 36/2005"]
    }


class BuildingPermitNavigator:
    """Main class for IMB navigation."""
    
    def __init__(self, retriever=None, model=None):
        self.retriever = retriever
        self.model = model
    
    def navigate(
        self,
        building_type: str,
        location: str,
        floor_area_m2: float,
        land_area_m2: float,
        building_height_m: Optional[float] = None,
        building_function: str = "hunian"
    ) -> Dict:
        """Generate complete IMB process guidance."""
        return get_imb_checklist(
            building_type, location, floor_area_m2,
            building_height_m, land_area_m2, building_function
        )
    
    def format_navigation(self, guidance: Dict) -> str:
        """Format guidance as readable text."""
        ret = guidance["retribution"]
        
        lines = [
            f"=== PANDUAN PENGURUSAN IMB ===",
            f"Tipe Bangunan: {guidance['building_type'].replace('_', ' ').title()}",
            f"Lokasi: {location}",
            f"Luas Lantai: {guidance['floor_area_m2']} m2",
            f"Luas Tanah: {guidance['land_area_m2']} m2",
            f"Fungsi: {guidance['building_function']}",
            f"",
            f"RETRIBUSI IMB:",
            f"  {ret['breakdown']}",
            f"  Total: Rp {ret['total_retribution_idr']:,.0f}",
            f"",
            f"ESTIMASI TOTAL BIAYA: Rp {guidance['estimated_total_cost_idr']:,.0f}",
            f"ESTIMASI WAKTU: {guidance['estimated_total_days']} hari",
            f"",
            f"LANGKAH-LANGKAH:"
        ]
        
        for step in guidance["imb_steps"]:
            lines.append(f"  STEP {step['step']}: {step['name']}")
            lines.append(f"    {step['description']}")
            lines.append(f"    Estimasi waktu: {step['estimated_days']}")
            if step.get("estimated_cost_idr"):
                lines.append(f"    Estimasi biaya: Rp {step['estimated_cost_idr']:,.0f}")
            if step.get("note"):
                lines.append(f"    Catatan: {step['note']}")
            lines.append(f"    Dokumen:")
            for doc in step["required_docs"]:
                lines.append(f"      - [ ] {doc}")
        
        if guidance.get("additional_requirements"):
            lines.append(f"")
            lines.append(f"PERSYARATAN TAMBAHAN:")
            for req in guidance["additional_requirements"]:
                lines.append(f"  - {req}")
        
        lines.append(f"")
        lines.append(f"REFERENSI:")
        for ref in guidance.get("sni_references", []):
            lines.append(f"  - {ref}")
        
        return "\n".join(lines)