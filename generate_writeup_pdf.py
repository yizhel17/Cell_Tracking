#!/usr/bin/env python3
"""Build the PDF report from the automatically generated analysis artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

# The dependency was installed in /tmp for this sandboxed run. A normal user
# installation from requirements.txt does not need this fallback.
temporary_dependencies = Path("/tmp/cell_tracking_pdf_deps")
if temporary_dependencies.exists():
    sys.path.insert(0, str(temporary_dependencies))

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output" / "pdf" / "cell_tracking_writeup.pdf"
FIGURES = ROOT / "figures"

NAVY = colors.HexColor("#12344D")
TEAL = colors.HexColor("#177E89")
PALE = colors.HexColor("#EAF4F4")
INK = colors.HexColor("#23323D")
MUTED = colors.HexColor("#5B6B75")


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=30,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Subtitle",
            parent=styles["Normal"],
            fontSize=12,
            leading=17,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=9,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Subsection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=TEAL,
            spaceBefore=7,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyCompact",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.3,
            leading=13.2,
            textColor=INK,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            fontSize=7.8,
            leading=10.5,
            textColor=MUTED,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CalloutNumber",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=25,
            textColor=TEAL,
            alignment=TA_CENTER,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CalloutLabel",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=MUTED,
            alignment=TA_CENTER,
        )
    )
    return styles


def header_footer(canvas, document):
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 0.28 * inch, width, 0.28 * inch, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(0.7 * inch, 0.42 * inch, "UCI Cell Tracking Challenge - Classical CV Baseline")
    canvas.drawRightString(width - 0.7 * inch, 0.42 * inch, f"Page {document.page}")
    canvas.restoreState()


def bullet(text: str, styles) -> Paragraph:
    return Paragraph(f"&bull;&nbsp; {text}", styles["BodyCompact"])


def scaled_image(path: Path, width: float) -> Image:
    image = Image(str(path))
    image.drawHeight = width * image.imageHeight / image.imageWidth
    image.drawWidth = width
    return image


def callout(value: str, label: str, styles):
    return [
        Paragraph(value, styles["CalloutNumber"]),
        Paragraph(label, styles["CalloutLabel"]),
    ]


def build_report() -> None:
    required_figures = [
        FIGURES / "count_over_time.png",
        FIGURES / "frame_first_pipeline.png",
        FIGURES / "frame_middle_pipeline.png",
        FIGURES / "frame_last_pipeline.png",
    ]
    missing = [str(path) for path in required_figures if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Run cell_count.py first; missing: {missing}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = build_styles()
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        rightMargin=0.68 * inch,
        leftMargin=0.68 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.68 * inch,
        title="Cell Tracking Challenge: Classical CV Baseline",
        author="Undergraduate Research Challenge Submission",
        subject="Automatic bacteria counting from an animated microscopy GIF",
    )
    story = []

    story.extend(
        [
            Spacer(1, 0.55 * inch),
            Paragraph("Cell Tracking Challenge", styles["ReportTitle"]),
            Paragraph(
                "A reproducible classical computer vision baseline for counting moving and growing bacteria",
                styles["Subtitle"],
            ),
            Spacer(1, 0.2 * inch),
        ]
    )
    summary = Table(
        [
            callout("40", "animated frames", styles)
            + callout("640 x 240", "full frame size", styles)
            + callout("3 to 19", "estimated count range", styles)
        ],
        colWidths=[1.55 * inch] * 6,
    )
    summary.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (1, 0)),
                ("SPAN", (2, 0), (3, 0)),
                ("SPAN", (4, 0), (5, 0)),
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.7, TEAL),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    story.extend(
        [
            summary,
            Spacer(1, 0.35 * inch),
            Paragraph("Objective", styles["Section"]),
            Paragraph(
                "Estimate the number of bacteria automatically in every frame of the supplied animated GIF. "
                "Only the left-half real microscopy image is analyzed; the right-hand laboratory tracking "
                "visualization is not used as an answer source.",
                styles["BodyCompact"],
            ),
            Paragraph("Approach in one sentence", styles["Subsection"]),
            Paragraph(
                "Highlight locally dark rods by subtracting a lightly denoised image from a broad background "
                "estimate, then apply Otsu thresholding, morphological opening, connected components, and "
                "area filtering.",
                styles["BodyCompact"],
            ),
            Paragraph("Scope and evidence", styles["Subsection"]),
            bullet("All 40 frames are processed by the same parameters; no frame-specific answer is hard-coded.", styles),
            bullet("Output format is one integer per line, and its length is asserted against GIF metadata.", styles),
            bullet("No ground truth is supplied, so the report presents sanity checks rather than accuracy claims.", styles),
        ]
    )

    story.extend(
        [
            PageBreak(),
            Paragraph("Dataset and Method", styles["Section"]),
            Paragraph(
                "The GIF contains 40 consistently sized RGB frames with array shape (240, 640, 3). The "
                "algorithm crops columns 0-319 before any image processing, ensuring that the right-half "
                "visualization cannot influence detection.",
                styles["BodyCompact"],
            ),
            Paragraph("Processing pipeline", styles["Subsection"]),
        ]
    )
    for item in [
        "Convert the 320 x 240 microscopy crop to 8-bit grayscale.",
        "Apply Gaussian denoising with radius 1 pixel.",
        "Estimate slow background illumination with Gaussian radius 10 pixels.",
        "Compute background minus denoised intensity so dark rods have positive local contrast.",
        "Choose a per-frame Otsu threshold, with a minimum response of 12 gray levels.",
        "Apply a 3 x 3 morphological opening to suppress isolated texture.",
        "Label 8-connected components and retain areas from 20 through 500 pixels.",
        "Write the retained component count for the frame.",
    ]:
        story.append(bullet(item, styles))

    parameter_data = [
        ["Parameter", "Value", "Purpose"],
        ["Denoise radius", "1 px", "Suppress pixel-scale texture"],
        ["Background radius", "10 px", "Remove slow illumination variation"],
        ["Threshold", "Otsu; floor 12", "Adapt automatically per frame"],
        ["Morphology", "3 x 3 opening", "Remove tiny isolated responses"],
        ["Component area", "20-500 px", "Reject speckles and broad artifacts"],
        ["Connectivity", "8", "Keep diagonal rod pixels connected"],
    ]
    table = Table(parameter_data, colWidths=[1.55 * inch, 1.25 * inch, 3.8 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#A8BBC3")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend(
        [
            Spacer(1, 0.08 * inch),
            table,
            Spacer(1, 0.12 * inch),
            Paragraph("Why classical CV?", styles["Subsection"]),
            Paragraph(
                "The animation is small, the cells have consistent local appearance, and the requested task "
                "is counting. This approach is inspectable, requires no labels or pretrained detector, and "
                "makes segmentation errors visible in a binary mask.",
                styles["BodyCompact"],
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            Paragraph("Results and Sanity Checks", styles["Section"]),
            scaled_image(FIGURES / "count_over_time.png", 6.7 * inch),
            Paragraph(
                "Figure 1. Estimated bacteria count by zero-based frame index. Monotonic growth was not "
                "forced; the small downward changes remain visible as segmentation uncertainty.",
                styles["Small"],
            ),
            Spacer(1, 0.08 * inch),
        ]
    )
    result_data = [
        ["Frame (zero-based)", "Estimated count", "Interpretation"],
        ["0", "3", "Small initial colony; three dark cores retained"],
        ["20", "8", "Mid-sequence growth with separated rods"],
        ["39", "19", "Dense final colony; contact risk is highest"],
        ["All frames", "3-19", "Overall range; 40 output lines"],
    ]
    result_table = Table(result_data, colWidths=[1.45 * inch, 1.25 * inch, 3.9 * inch])
    result_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TEAL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#A8BBC3")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend(
        [
            result_table,
            Spacer(1, 0.12 * inch),
            Paragraph("Observed temporal behavior", styles["Subsection"]),
            Paragraph(
                "The sequence generally increases from 3 to 19. Most adjacent changes are 0 or +1. The "
                "largest change is +3 at frame 39; frame 32 changes by +2. Two -1 changes occur, consistent "
                "with a marginal component merging or dropping below threshold rather than a manually "
                "smoothed output.",
                styles["BodyCompact"],
            ),
            Paragraph(
                "These observations make the output plausible, but they do not establish correctness without "
                "independent cell annotations.",
                styles["BodyCompact"],
            ),
        ]
    )

    story.extend([PageBreak(), Paragraph("Qualitative Segmentation Checks", styles["Section"])])
    for number, (label, filename, count) in enumerate(
        [
            ("First frame", "frame_first_pipeline.png", 3),
            ("Middle frame", "frame_middle_pipeline.png", 8),
            ("Last frame", "frame_last_pipeline.png", 19),
        ],
        start=2,
    ):
        image = scaled_image(FIGURES / filename, 6.7 * inch)
        caption = Paragraph(
            f"Figure {number}. {label}: microscopy crop, grayscale image, binary mask, and retained "
            f"component boxes. Estimated count = {count}.",
            styles["Small"],
        )
        story.append(KeepTogether([image, caption, Spacer(1, 0.08 * inch)]))

    story.extend(
        [
            PageBreak(),
            Paragraph("Failure Analysis and Limitations", styles["Section"]),
            Paragraph("Noise and uneven illumination", styles["Subsection"]),
            Paragraph(
                "GIF compression texture and background gradients can resemble weak dark objects. Local "
                "background subtraction, opening, and area filtering remove most of this signal, but a strong "
                "artifact could still survive.",
                styles["BodyCompact"],
            ),
            Paragraph("Touching cells and dense colonies", styles["Subsection"]),
            Paragraph(
                "Connected components can merge two touching dark cores, causing undercount. The risk rises "
                "in late frames. Conversely, a broken response along one rod can form two retained components "
                "and cause overcount.",
                styles["BodyCompact"],
            ),
            Paragraph("Low contrast and area filtering", styles["Subsection"]),
            Paragraph(
                "A faint cell may fall below Otsu's threshold or below the 20-pixel area cutoff. A large merged "
                "group could exceed 500 pixels. These fixed area limits may not transfer to other magnifications.",
                styles["BodyCompact"],
            ),
            Paragraph("Why watershed was not added", styles["Subsection"]),
            Paragraph(
                "The inspected dark cores are mostly separated, and the count curve is stable. Without ground "
                "truth, marker-controlled watershed would add tuning freedom and could split single rods. It "
                "is worth testing only after annotating dense late frames and measuring split errors.",
                styles["BodyCompact"],
            ),
            Paragraph("Possible improvements", styles["Subsection"]),
            bullet("Annotate representative early, middle, and dense late frames for objective parameter validation.", styles),
            bullet("Evaluate watershed only on confirmed merged components.", styles),
            bullet("Use temporal correspondence to distinguish division from segmentation flicker.", styles),
            bullet("Extend from per-frame counting to cell identity, lineage, and true tracking.", styles),
            Paragraph("References", styles["Section"]),
            Paragraph(
                "1. Pillow ImageSequence documentation: pillow.readthedocs.io/en/stable/reference/ImageSequence.html<br/>"
                "2. Pillow ImageFilter documentation: pillow.readthedocs.io/en/stable/reference/ImageFilter.html<br/>"
                "3. NumPy sliding_window_view documentation: numpy.org/doc/stable/reference/generated/"
                "numpy.lib.stride_tricks.sliding_window_view.html<br/>"
                "4. Matplotlib savefig documentation: matplotlib.org/stable/api/_as_gen/"
                "matplotlib.pyplot.savefig.html",
                styles["Small"],
            ),
            Spacer(1, 0.1 * inch),
            Paragraph(
                "The professor's published 2D-case paper was not used to construct this solution.",
                styles["Small"],
            ),
        ]
    )

    document.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(OUTPUT)


if __name__ == "__main__":
    build_report()
