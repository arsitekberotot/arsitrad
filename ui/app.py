"""Gradio UI for Arsitrad — unified chat interface for all advisory modules."""

import gradio as gr
import json
from typing import Optional
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.disaster import DisasterDamageReporter
from agent.settlement import SettlementUpgradingAdvisor
from agent.permit import BuildingPermitNavigator
from agent.cooling import PassiveCoolingAdvisor


class ArsitradUI:
    """Main UI controller — manages chat state and routes to correct module."""
    
    def __init__(self):
        # Initialize all modules
        self.disaster_reporter = DisasterDamageReporter()
        self.settlement_advisor = SettlementUpgradingAdvisor()
        self.permit_navigator = BuildingPermitNavigator()
        self.cooling_advisor = PassiveCoolingAdvisor()
        
        self.chat_history = []
    
    def route_and_respond(self, message: str, history: list) -> tuple:
        """Analyze user message and route to correct module."""
        message_lower = message.lower()
        
        # Route based on keywords
        if any(kw in message_lower for kw in ["gempa", "banjir", "tsunami", "longsor", "rusak", "kerusakan", "bencana"]):
            return self._handle_disaster(message, history)
        elif any(kw in message_lower for kw in ["imb", "izin", "mendirikan", "bangunan", "izin mendirikan"]):
            return self._handle_permit(message, history)
        elif any(kw in message_lower for kw in ["permukiman", "settlemen", "kampung", "tidak layak", "bantaran"]):
            return self._handle_settlement(message, history)
        elif any(kw in message_lower for kw in ["dingin", "panas", "pendingin", "cooling", "ventilasi", "thermal"]):
            return self._handle_cooling(message, history)
        else:
            return self._handle_regulation(message, history)
    
    def _handle_disaster(self, message: str, history: list) -> tuple:
        response = "[MODUL: Disaster Damage Reporter]\n\n"
        response += "Untuk laporan kerusakan bencana, saya memerlukan informasi berikut:\n"
        response += "- Lokasi\n- Tipe bencana (gempa/banjir/tsunami/longsor)\n"
        response += "- Tipe bangunan\n- Deskripsi kerusakan\n\n"
        response += "Contoh: 'Gempa di Cianjur, rumah tinggal, dinding retak diagonal, atap bergeser'"
        return response, history + [(message, response)]
    
    def _handle_permit(self, message: str, history: list) -> tuple:
        response = "[MODUL: Building Permit Navigator]\n\n"
        response += "Saya bisa membantu mengurus IMB. Berikan info:\n"
        response += "- Tipe bangunan\n- Lokasi\n- Luas lantai (m2)\n"
        response += "- Luas tanah (m2)\n\n"
        response += "Contoh: 'Rumah tinggal di Jakarta Selatan, luas lantai 120m2, tanah 200m2'"
        return response, history + [(message, response)]
    
    def _handle_settlement(self, message: str, history: list) -> tuple:
        response = "[MODUL: Settlement Upgrading Advisor]\n\n"
        response += "Untuk analisis permukiman, berikan:\n"
        response += "- Lokasi\n- Kepadatan penduduk (orang/ha)\n"
        response += "- Infrastruktur yang ada saat ini\n"
        response += "- Budget yang tersedia\n\n"
        response += "Contoh: 'Kampung di Surabaya, 500 orang/ha, hanya listrik dan air sumur, budget 500 juta'"
        return response, history + [(message, response)]
    
    def _handle_cooling(self, message: str, history: list) -> tuple:
        response = "[MODUL: Passive Cooling Advisor]\n\n"
        response += "Untuk saran passive cooling, berikan:\n"
        response += "- Dimensi bangunan (panjang x lebar x tinggi)\n"
        response += "- Orientasi bangunan\n"
        response += "- Material dinding dan atap\n"
        response += "- Zona iklim\n\n"
        response += "Contoh: 'Rumah 8x10x3.5m, orientasi timur-barat, dinding bata, atap genteng, zona pesisir'"
        return response, history + [(message, response)]
    
    def _handle_regulation(self, message: str, history: list) -> tuple:
        response = "[MODUL: Regulation RAG]\n\n"
        response += f"Searching regulations for: '{message}'...\n\n"
        response += "[Placeholder: Dalam implementasi penuh, ini akan mengembalikan jawaban "
        response += "yang grounding dengan SNI/UU/PP terkait menggunakan RAG + Gemma 4 fine-tuned.]"
        return response, history + [(message, response)]
    
    def process_disaster_report(
        self,
        location: str,
        disaster_type: str,
        building_type: str,
        damage_description: str,
        floor_area: str
    ) -> str:
        """Process full disaster report form."""
        try:
            floor_m2 = float(floor_area) if floor_area else None
            result = self.disaster_reporter.report(
                location=location,
                disaster_type=disaster_type,
                building_type=building_type,
                damage_description=damage_description,
                floor_area_m2=floor_m2
            )
            return self.disaster_reporter.format_report(result)
        except Exception as e:
            return f"Error: {str(e)}"
    
    def process_permit_navigation(
        self,
        building_type: str,
        location: str,
        floor_area: str,
        land_area: str,
        height: str,
        function: str
    ) -> str:
        """Process full permit navigation form."""
        try:
            floor_m2 = float(floor_area)
            land_m2 = float(land_area)
            height_m = float(height) if height else None
            result = self.permit_navigator.navigate(
                building_type=building_type,
                location=location,
                floor_area_m2=floor_m2,
                land_area_m2=land_m2,
                building_height_m=height_m,
                building_function=function
            )
            return self.permit_navigator.format_navigation(result)
        except Exception as e:
            return f"Error: {str(e)}"
    
    def process_cooling_advice(
        self,
        length: str,
        width: str,
        height: str,
        floors: str,
        orientation: str,
        wall_material: str,
        roof_material: str,
        climate_zone: str,
        budget: str
    ) -> str:
        """Process full cooling advice form."""
        try:
            dimensions = {
                "length_m": float(length),
                "width_m": float(width),
                "height_m": float(height),
                "floor_count": int(floors) if floors else 1
            }
            materials = {
                "wall_material": wall_material,
                "roof_material": roof_material
            }
            budget_idr = float(budget) if budget else None
            
            result = self.cooling_advisor.advise(
                dimensions=dimensions,
                orientation=orientation,
                materials=materials,
                climate_zone=climate_zone,
                budget_idr=budget_idr
            )
            return self.cooling_advisor.format_advice(result)
        except Exception as e:
            return f"Error: {str(e)}"


def create_ui():
    """Build Gradio interface."""
    app = ArsitradUI()
    
    with gr.Blocks(
        title="Arsitrad — Indonesian Architecture AI Advisor",
        theme=gr.themes.Default(
            primary_hue="blue",
            secondary_hue="teal",
        )
    ) as interface:
        gr.Markdown("""
        # Arsitrad
        ## Indonesian Architecture AI Advisor

        AI assistant untuk regulasi bangunan Indonesia, оценка kerusakan bencana, navigasi IMB, dan passive cooling design.

        Powered by Gemma 4 (fine-tuned) + RAG pipeline + function calling.
        """)
        
        with gr.Tabs():
            # Tab 1: Chat
            with gr.TabItem("💬 Chat"):
                gr.ChatInterface(
                    fn=app.route_and_respond,
                    title="Arsitrad Chat",
                    description="Ajukan pertanyaan tentang regulasi bangunan, kerusakan bencana, IMB, atau passive cooling",
                    examples=[
                        ["Gempa di Cianjur, rumah tinggal dinding retak dan atap geser"],
                        ["Rumah 120m2 di Jakarta Selatan, caraurus IMB?"],
                        ["Kampung tidak layak di Surabaya dengan budget 500 juta"],
                        ["Tips passive cooling untuk bangunan 8x10m di zona pesisir"]
                    ]
                )
            
            # Tab 2: Disaster Reporter
            with gr.TabItem("🌋 Disaster Damage Reporter"):
                gr.Markdown("### Laporan Kerusakan Bencana")
                with gr.Row():
                    with gr.Column():
                        location = gr.Textbox(label="Lokasi", placeholder="Contoh: Cianjur, Jawa Barat")
                        disaster_type = gr.Dropdown(
                            ["gempa", "banjir", "tsunami", "longsor", "puting_beliung", "kebakaran"],
                            label="Tipe Bencana",
                            value="gempa"
                        )
                        building_type = gr.Dropdown(
                            ["rumah_tinggal", "gedung_perkantoran", "sekolah", "pasar", "lainnya"],
                            label="Tipe Bangunan",
                            value="rumah_tinggal"
                        )
                        damage_description = gr.Textbox(
                            label="Deskripsi Kerusakan",
                            placeholder="Deskripsikan kerusakan yang terlihat...",
                            lines=3
                        )
                        floor_area = gr.Textbox(label="Luas Lantai (m2) - opsional", placeholder="Contoh: 60")
                        disaster_submit = gr.Button("Generate Laporan", variant="primary")
                
                disaster_output = gr.Textbox(label="Laporan", lines=15, show_copy_button=True)
                
                disaster_submit.click(
                    fn=app.process_disaster_report,
                    inputs=[location, disaster_type, building_type, damage_description, floor_area],
                    outputs=disaster_output
                )
            
            # Tab 3: Building Permit
            with gr.TabItem("📋 IMB Navigator"):
                gr.Markdown("### Navigasi Izin Mendirikan Bangunan (IMB)")
                with gr.Row():
                    with gr.Column():
                        building_type = gr.Dropdown(
                            ["rumah_tinggal", "apartemen", "gedung_komersial", "gedung_industri", "fasilitas_umum"],
                            label="Tipe Bangunan",
                            value="rumah_tinggal"
                        )
                        location = gr.Textbox(label="Lokasi", placeholder="Contoh: Jakarta Selatan")
                        floor_area = gr.Textbox(label="Luas Lantai (m2)", placeholder="Contoh: 120")
                        land_area = gr.Textbox(label="Luas Tanah (m2)", placeholder="Contoh: 200")
                        height = gr.Textbox(label="Tinggi Bangunan (m) - opsional", placeholder="Contoh: 8")
                        function = gr.Dropdown(
                            ["hunian", "usaha", "campuran"],
                            label="Fungsi Bangunan",
                            value="hunian"
                        )
                        permit_submit = gr.Button("Generate Panduan IMB", variant="primary")
                
                permit_output = gr.Textbox(label="Panduan IMB", lines=20, show_copy_button=True)
                
                permit_submit.click(
                    fn=app.process_permit_navigation,
                    inputs=[building_type, location, floor_area, land_area, height, function],
                    outputs=permit_output
                )
            
            # Tab 4: Passive Cooling
            with gr.TabItem("❄️ Passive Cooling Advisor"):
                gr.Markdown("### Saran Passive Cooling untuk Bangunan Tropis")
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Dimensi Bangunan")
                        length = gr.Textbox(label="Panjang (m)", placeholder="8")
                        width = gr.Textbox(label="Lebar (m)", placeholder="10")
                        height = gr.Textbox(label="Tinggi (m)", placeholder="3.5")
                        floors = gr.Textbox(label="Jumlah Lantai", placeholder="1")
                        orientation = gr.Dropdown(
                            ["utara", "selatan", "timur", "barat"],
                            label="Orientasi Utama",
                            value="barat"
                        )
                        gr.Markdown("#### Material")
                        wall_material = gr.Dropdown(
                            ["bata", "beton", "kayu", "batako", "hebel"],
                            label="Material Dinding",
                            value="bata"
                        )
                        roof_material = gr.Dropdown(
                            ["genteng", "metal", "beton"],
                            label="Material Atap",
                            value="genteng"
                        )
                        climate_zone = gr.Dropdown(
                            ["dataran_rendah_pesisir", "dataran_tinggi", "tropical_basah", "tropical_kering"],
                            label="Zona Iklim",
                            value="dataran_rendah_pesisir"
                        )
                        budget = gr.Textbox(label="Budget (IDR) - opsional", placeholder="Contoh: 5000000")
                        cooling_submit = gr.Button("Generate Saran", variant="primary")
                
                cooling_output = gr.Textbox(label="Saran Passive Cooling", lines=20, show_copy_button=True)
                
                cooling_submit.click(
                    fn=app.process_cooling_advice,
                    inputs=[length, width, height, floors, orientation, wall_material, roof_material, climate_zone, budget],
                    outputs=cooling_output
                )
        
        gr.Markdown("""
        ---
        **Arsitrad** — Built for the Gemma 4 Good Hackathon
        
        Tech stack: Gemma 4 (QLoRA fine-tuned) + RAG + Function Calling + Gradio
        
        Indonesian building regulations: SNI, UU No. 28/2002, PP No. 36/2005
        """)

    return interface


if __name__ == "__main__":
    ui = create_ui()
    ui.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )