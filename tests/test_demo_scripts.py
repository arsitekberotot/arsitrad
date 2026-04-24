from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_legacy_streamlit_fallback_script_is_documented_and_smoke_safe():
    script = REPO_ROOT / "scripts" / "run_legacy_streamlit.sh"
    rollback_doc = REPO_ROOT / "docs" / "rollback-runbook.md"

    assert script.exists()
    assert script.stat().st_mode & 0o111

    script_text = script.read_text(encoding="utf-8")
    assert "--smoke-only" in script_text
    assert "legacy/streamlit_app.py" in script_text
    assert "streamlit run" in script_text

    doc_text = rollback_doc.read_text(encoding="utf-8")
    assert "./scripts/run_legacy_streamlit.sh" in doc_text
    assert "./scripts/run_web_demo.sh" in doc_text
    assert "streamlit run ui/app.py" in doc_text


def test_demo_deployment_links_to_rollback_runbook():
    demo_doc = (REPO_ROOT / "docs" / "demo-deployment.md").read_text(encoding="utf-8")

    assert "rollback-runbook.md" in demo_doc
    assert "./scripts/run_legacy_streamlit.sh" in demo_doc
