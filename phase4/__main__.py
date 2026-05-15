"""Run the Phase 4 API with ``python -m phase4`` (dev defaults)."""

from __future__ import annotations


def main() -> None:
    import uvicorn

    uvicorn.run("phase4.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
