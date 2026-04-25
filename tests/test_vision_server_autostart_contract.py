from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_local_web_demo_autostarts_llama_cpp_vision_server_before_backend():
    script = read("scripts/run_web_demo.sh")

    assert "ARSITRAD_VISION_AUTOSTART" in script
    assert "VISION_PID" in script
    assert "llama-server" in script
    assert "--mmproj" in script
    assert "ARSITRAD_VISION_BASE_URL" in script
    assert script.index("start_vision_server") < script.index("python -m uvicorn api.server:app")


def test_cloudflare_demo_also_autostarts_vision_for_judge_demo():
    script = read("scripts/run_cloudflare_demo.sh")

    assert "ARSITRAD_VISION_AUTOSTART" in script
    assert "VISION_PID" in script
    assert "start_vision_server" in script
    assert "ARSITRAD_VISION_BASE_URL" in script
    assert script.index("start_vision_server") < script.index("python -m uvicorn api.server:app")


def test_readme_documents_always_on_vision_runtime_and_model_paths():
    readme = read("README.md")

    assert "Vision auto-start" in readme
    assert "ARSITRAD_VISION_AUTOSTART=1" in readme
    assert "ARSITRAD_VISION_MODEL_PATH" in readme
    assert "ARSITRAD_VISION_MMPROJ_PATH" in readme
    assert "ARSITRAD_REQUIRE_VISION=1" in readme
