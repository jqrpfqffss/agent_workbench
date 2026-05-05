from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZipFile


EXPECTED_SLIDES = 12
PPT_PATH = Path(__file__).resolve().parent / "AGENT_WORKBENCH_PPT_V4_ZH.pptx"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    require(PPT_PATH.exists(), f"missing pptx: {PPT_PATH}")

    with ZipFile(PPT_PATH) as zf:
        names = zf.namelist()
        slide_xml = sorted(
            name
            for name in names
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        )
        note_xml = sorted(
            name
            for name in names
            if name.startswith("ppt/notesSlides/notesSlide") and name.endswith(".xml")
        )
        media_files = [
            name
            for name in names
            if name.startswith("ppt/media/") and not name.endswith("/")
        ]

        require(len(slide_xml) == EXPECTED_SLIDES, f"expected {EXPECTED_SLIDES} slides, got {len(slide_xml)}")
        require(len(note_xml) == EXPECTED_SLIDES, f"expected {EXPECTED_SLIDES} notes slides, got {len(note_xml)}")
        require(
            not media_files,
            f"expected no embedded media assets for an editable deck, found: {media_files}",
        )

        all_slide_text = []
        for name in slide_xml:
            all_slide_text.append(zf.read(name).decode("utf-8", errors="ignore"))
        merged = "\n".join(all_slide_text)

        required_snippets = [
            "agent_workbench",
            "STM32 UART CLI ready.",
            "cli_automation_regression",
            "session_summary.md",
            "integration install continue",
            "TIM1_CH1",
        ]
        missing = [snippet for snippet in required_snippets if snippet not in merged]
        require(not missing, f"missing expected snippets: {missing}")

    print(f"pptx={PPT_PATH}")
    print(f"slides={EXPECTED_SLIDES}")
    print("notes=ok")
    print("editable_media=ok")
    print("content_snippets=ok")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
