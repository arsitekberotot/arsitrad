from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_next_page_locks_viewport_and_only_chat_messages_scroll():
    globals_css = read("web/src/app/globals.css")
    page = read("web/src/app/page.tsx")
    workbench = read("web/src/components/arsitrad-workbench.tsx")

    assert "height: 100vh" in globals_css
    assert "overflow: hidden" in globals_css
    assert "h-screen" in page
    assert "overflow-hidden" in page
    assert 'data-testid="chat-scroll-container"' in workbench
    assert "overflow-y-auto" in workbench
    assert 'data-testid="chat-input-area"' in workbench
    assert "shrink-0" in workbench


def test_chat_input_supports_image_attachments_and_sends_payload():
    workbench = read("web/src/components/arsitrad-workbench.tsx")
    api = read("web/src/lib/api.ts")
    types = read("web/src/lib/types.ts")

    assert 'type="file"' in workbench
    assert 'accept="image/*"' in workbench
    assert "readAsDataURL" in workbench
    assert "attachedImages" in workbench
    assert "images" in api
    assert "ImageAttachment" in types
