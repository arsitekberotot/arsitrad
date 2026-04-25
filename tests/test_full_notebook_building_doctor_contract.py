import ast
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = REPO_ROOT / "Arsitrad-Full.ipynb"


def load_notebook():
    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def joined_cells():
    return ["".join(cell.get("source", [])) for cell in load_notebook()["cells"]]


def test_full_notebook_downloads_gemma_mmproj_for_building_doctor():
    cells = joined_cells()
    download_cell = next(src for src in cells if "hf_hub_download" in src and "gemma-4-E4B-it-Q4_K_M.gguf" in src)

    assert "mmproj-gemma-4-E4B-it-Q8_0.gguf" in download_cell
    assert "ARSITRAD_VISION_MODEL_PATH" in download_cell
    assert "ARSITRAD_VISION_MMPROJ_PATH" in download_cell


def test_full_notebook_starts_vision_bridge_before_fastapi_backend():
    cells = joined_cells()
    backend_cell = next(src for src in cells if "uvicorn" in src and "api.server:app" in src)

    assert "ensure_llama_server" in backend_cell
    assert "start_vision_server" in backend_cell
    assert "llama-server" in backend_cell
    assert "--mmproj" in backend_cell
    assert "ARSITRAD_REQUIRE_VISION" in backend_cell
    assert "ARSITRAD_VISION_BASE_URL" in backend_cell
    assert "Gemma vision bridge local URL" in backend_cell
    assert backend_cell.index("start_vision_server") < backend_cell.index("python -m uvicorn")
    assert "vision_enabled" in backend_cell


def test_full_notebook_frontend_cell_verifies_building_doctor_vision_status():
    cells = joined_cells()
    frontend_cell = next(src for src in cells if "NEXT_PUBLIC_API_BASE_URL" in src and "next start" in src)

    assert "vision_enabled" in frontend_cell
    assert "Building Doctor" in frontend_cell
    assert "AI Advisor" in frontend_cell
    assert "metadata-only" in frontend_cell
    assert "next start" in frontend_cell
    assert "npm run build" in frontend_cell


def test_full_notebook_copy_mentions_ai_advisor_building_doctor():
    notebook_text = NOTEBOOK_PATH.read_text(encoding="utf-8")

    assert "AI Advisor" in notebook_text
    assert "Building Doctor" in notebook_text
    assert "visual triage" in notebook_text
    assert "Regulation Q&A Assistant" not in notebook_text


def test_full_notebook_code_cells_parse_after_patch():
    nb = load_notebook()
    for index, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        stripped = src.lstrip()
        if stripped.startswith("%") or stripped.startswith("!"):
            continue
        ast.parse(src, filename=f"Arsitrad-Full.ipynb cell {index}")
