"""Settlement Upgrading Advisor — prioritizes improvements for informal settlements."""

from typing import Dict, List


# Indonesian housing standards (UU 1/2011, SNI for housing quality)
MINIMUM_STANDARDS = {
    "air_bersih": {
        "min_per_capita_lpd": 60,
        "description": "Akses air bersih minimal 60 liter per orang per hari",
        "cost_per_unit_idr": 500000
    },
    "sanitasi": {
        "min_toilet_ratio": "1 per 5 keluarga",
        "description": "MCK layak dengan sept tank komunal",
        "cost_per_unit_idr": 2500000
    },
    "listrik": {
        "min_watt_per_rumah": 450,
        "description": "Akses listrik 450VA minimum",
        "cost_per_unit_idr": 1000000
    },
    "jalan": {
        "min_lebar_m": 1.5,
        "description": "Jalan pejalan kaki minimal 1.5m",
        "cost_per_m2_idr": 750000
    },
    "drainase": {
        "description": "Sistem drainase untuk mencegah banjir",
        "cost_per_m_idr": 1500000
    }
}


def calculate_upgrading_score(
    population_density: float,
    current_infrastructure: str
) -> Dict:
    """Calculate current infrastructure score and gaps."""
    infra_lower = current_infrastructure.lower()
    
    score = {
        "air_bersih": 0,
        "sanitasi": 0,
        "listrik": 0,
        "jalan": 0,
        "drainase": 0
    }
    
    # Keyword-based scoring (simplified)
    if any(k in infra_lower for k in ["air", "pam", "sumur", "depok", "晋江"]):
        score["air_bersih"] = 1
    if any(k in infra_lower for k in ["toilet", "kamar mandi", "mc", "septik"]):
        score["sanitasi"] = 1
    if any(k in infra_lower for k in ["listrik", "pln", "tegangan"]):
        score["listrik"] = 1
    if any(k in infra_lower for k in ["jalan", "aspal", "beton", "paving"]):
        score["jalan"] = 1
    if any(k in infra_lower for k in ["drainase", "selokan", "saluran air"]):
        score["drainase"] = 1
    
    total_score = sum(score.values()) / len(score) * 100
    
    gaps = [k for k, v in score.items() if v == 0]
    
    return {
        "current_score": round(total_score, 1),
        "component_scores": score,
        "gaps": gaps,
        "infrastructure_level": "baik" if total_score >= 80 else "sedang" if total_score >= 50 else "buruk"
    }


def prioritize_upgrades(
    gaps: List[str],
    population_density: float,
    budget_constraint_idr: float,
    priority_goals: List[str]
) -> List[Dict]:
    """Prioritize upgrading interventions based on budget and goals."""
    interventions = []
    
    # Base interventions for each gap
    if "air_bersih" in gaps:
        interventions.append({
            "category": "air_bersih",
            "description": "Pemasangan pipa jaringan air bersih komunal",
            "impact_score": 9,
            "cost_per_unit_idr": MINIMUM_STANDARDS["air_bersih"]["cost_per_unit_idr"],
            "unit": "unit komunal",
            "eligible": True
        })
    
    if "sanitasi" in gaps:
        interventions.append({
            "category": "sanitasi",
            "description": "Pembangunan MCK komunal dengan sept tank",
            "impact_score": 8,
            "cost_per_unit_idr": MINIMUM_STANDARDS["sanitasi"]["cost_per_unit_idr"],
            "unit": "unit MCK",
            "eligible": True
        })
    
    if "listrik" in gaps:
        interventions.append({
            "category": "listrik",
            "description": "Penguatan jaringan listrik dan subsidi biaya pasang",
            "impact_score": 7,
            "cost_per_unit_idr": MINIMUM_STANDARDS["listrik"]["cost_per_unit_idr"],
            "unit": "koneksi rumah",
            "eligible": True
        })
    
    if "jalan" in gaps:
        interventions.append({
            "category": "jalan",
            "description": "Pemasangan paving block untuk jalan lingkungan",
            "impact_score": 6,
            "cost_per_unit_idr": MINIMUM_STANDARDS["jalan"]["cost_per_m2_idr"] * 50,  # per rumah
            "unit": "m2 jalan",
            "eligible": True
        })
    
    if "drainase" in gaps:
        interventions.append({
            "category": "drainase",
            "description": "Pemasangan saluran drainase komunal",
            "impact_score": 5,
            "cost_per_unit_idr": MINIMUM_STANDARDS["drainase"]["cost_per_m_idr"],
            "unit": "meter saluran",
            "eligible": True
        })
    
    # Apply budget constraint
    for interv in interventions:
        # Max affordable units within budget
        max_units = int(budget_constraint_idr / interv["cost_per_unit_idr"])
        interv["max_affordable_units"] = max_units
        interv["total_cost_if_fully_implemented"] = max_units * interv["cost_per_unit_idr"]
    
    # Sort by impact/cost ratio
    interventions.sort(key=lambda x: x["impact_score"] / max(x["cost_per_unit_idr"], 1), reverse=True)
    
    # Assign priority
    for i, interv in enumerate(interventions, 1):
        interv["priority_rank"] = i
    
    return interventions


class SettlementUpgradingAdvisor:
    """Main class for settlement upgrading advice."""
    
    def __init__(self, retriever=None, model=None):
        self.retriever = retriever
        self.model = model
    
    def advise(
        self,
        location: str,
        population_density: float,
        current_infrastructure: str,
        budget_constraint_idr: float,
        priority_goals: List[str] = None
    ) -> Dict:
        """Generate upgrading recommendations."""
        priority_goals = priority_goals or []
        
        # Step 1: Calculate current score
        assessment = calculate_upgrading_score(population_density, current_infrastructure)
        
        # Step 2: Prioritize interventions
        interventions = prioritize_upgrades(
            assessment["gaps"],
            population_density,
            budget_constraint_idr,
            priority_goals
        )
        
        # Step 3: Generate plan within budget
        recommended_plan = []
        remaining_budget = budget_constraint_idr
        
        for interv in interventions:
            if remaining_budget >= interv["cost_per_unit_idr"]:
                # Recommend full implementation for top priorities
                recommended_plan.append({
                    **interv,
                    "recommended_units": interv["max_affordable_units"],
                    "recommended_cost": interv["max_affordable_units"] * interv["cost_per_unit_idr"]
                })
                remaining_budget -= interv["recommended_cost"]
        
        return {
            "location": location,
            "population_density": population_density,
            "current_assessment": assessment,
            "recommended_plan": recommended_plan,
            "budget_used_idr": budget_constraint_idr - remaining_budget,
            "budget_remaining_idr": remaining_budget,
            "total_investment_needed_idr": sum(i["total_cost_if_fully_implemented"] for i in interventions)
        }
    
    def format_advice(self, advice: Dict) -> str:
        """Format advice as readable text."""
        assessment = advice["current_assessment"]
        plan = advice["recommended_plan"]
        
        lines = [
            f"=== ANALISIS PENINGKATAN LAYANAN PERMUKIMAN ===",
            f"Lokasi: {advice.get('location', 'N/A')}",
            f"Density Penduduk: {advice.get('population_density', 0):.0f} orang/ha",
            f"",
            f"SKOR INFRASTRUKTUR SAAT INI: {assessment['current_score']}/100",
            f"Tingkat: {assessment['infrastructure_level'].upper()}",
            f"",
            f"KOMPONEN:",
            *[f"  - {k.replace('_', ' ').title()}: {'ADA' if v else 'TIDAK ADA'}" 
              for k, v in assessment["component_scores"].items()],
            f"",
            f"GAP: {', '.join(assessment['gaps']) if assessment['gaps'] else 'Tidak ada'}",
            f"",
            f"REKOMENDASI PENINGKATAN (sesuai budget):"
        ]
        
        for interv in plan:
            lines.append(f"  PRIORITAS {interv['priority_rank']}: {interv['description']}")
            lines.append(f"    Kategori: {interv['category']}")
            lines.append(f"    Unit disarankan: {interv['recommended_units']} {interv['unit']}")
            lines.append(f"    Estimasi biaya: Rp {interv['recommended_cost']:,.0f}")
            lines.append(f"    Skor dampak: {interv['impact_score']}/10")
        
        lines.extend([
            f"",
            f"BUDGET:",
            f"  Digunakan: Rp {advice['budget_used_idr']:,.0f}",
            f"  Sisa: Rp {advice['budget_remaining_idr']:,.0f}",
            f"  Total investasi dibutuhkan: Rp {advice['total_investment_needed_idr']:,.0f}"
        ])
        
        return "\n".join(lines)