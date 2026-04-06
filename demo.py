"""Demo entry point — runs Arsitrad with all modules."""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import create_ui


if __name__ == "__main__":
    print("Starting Arsitrad...")
    print("Loading modules...")
    
    app = create_ui()
    
    print("Launching Gradio UI...")
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True  # Generate public link for demo
    )