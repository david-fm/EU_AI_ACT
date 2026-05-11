#!/usr/bin/env python3
"""Generate a PDF from a JSON assessment fixture and render preview images."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from eu_ai_act.reporting.exporters import export_assessment_pdf


class JsonAssessment:
    """Simple adapter exposing the `to_dict` API expected by the exporter."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, object]:
        return self._payload


def _render_with_pdfium(pdf_path: Path, image_dir: Path, scale: float = 2.2) -> int:
    import pypdfium2 as pdfium

    image_dir.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(str(pdf_path))
    rendered = 0
    for page_index in range(len(pdf)):
        page = pdf[page_index]
        pil_image = page.render(scale=scale).to_pil()
        image_path = image_dir / f"page-{page_index + 1:02d}.png"
        pil_image.save(image_path)
        rendered += 1
    return rendered


def _render_with_qlmanage(pdf_path: Path, image_dir: Path) -> int:
    """Fallback renderer for macOS. It generates a PNG preview (usually first page)."""

    image_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "qlmanage",
            "-t",
            "-s",
            "2200",
            "-o",
            str(image_dir),
            str(pdf_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    quicklook_name = f"{pdf_path.name}.png"
    quicklook_path = image_dir / quicklook_name
    if quicklook_path.exists():
        quicklook_path.rename(image_dir / "page-01.png")

    return 1 if (image_dir / "page-01.png").exists() else 0


def generate_preview(assessment_json: Path, output_pdf: Path, image_dir: Path) -> tuple[Path, int, str]:
    payload = json.loads(assessment_json.read_text(encoding="utf-8"))
    assessment = JsonAssessment(payload)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    export_assessment_pdf(assessment, output_pdf)

    renderer = "pypdfium2"
    try:
        pages = _render_with_pdfium(output_pdf, image_dir)
    except ModuleNotFoundError:
        renderer = "qlmanage"
        pages = _render_with_qlmanage(output_pdf, image_dir)

    return output_pdf, pages, renderer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and visually validate the compliance PDF exporter.")
    parser.add_argument(
        "--assessment-json",
        type=Path,
        default=Path("outputs/real_integration_test/assessment.json"),
        help="Path to the assessment JSON fixture.",
    )
    parser.add_argument(
        "--output-pdf",
        type=Path,
        default=Path("outputs/real_integration_test/assessment.preview.pdf"),
        help="Path where the PDF will be generated.",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("outputs/real_integration_test/assessment.preview.images"),
        help="Folder where preview images will be generated.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pdf_path, pages, renderer = generate_preview(args.assessment_json, args.output_pdf, args.image_dir)

    print(f"PDF generated: {pdf_path}")
    print(f"Renderer used: {renderer}")
    print(f"Preview images generated: {pages}")
    print(f"Images folder: {args.image_dir}")

    if renderer == "qlmanage":
        print("Tip: install pypdfium2 to render all pages: uv add pypdfium2")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
