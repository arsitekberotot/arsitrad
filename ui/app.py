from __future__ import annotations

"""Compatibility shim for the legacy Streamlit UI.

The maintained product UI now lives in `web/` (Next.js) and talks to
`api/server.py` (FastAPI). The old Streamlit implementation is kept under
`legacy/streamlit_app.py` for rollback/demo fallback.

`streamlit run ui/app.py` still works because this module re-exports the
legacy app and executes its `main()` on direct runs.
"""

from legacy.streamlit_app import *  # noqa: F401,F403
from legacy.streamlit_app import main as _legacy_main


if __name__ == "__main__":
    _legacy_main()
