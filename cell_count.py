#!/usr/bin/env python3
"""Automatically count bacteria in the microscopy half of an animated GIF.

The implementation intentionally uses a small, explainable classical computer
vision pipeline and does not inspect the tracking visualization on the right.
"""

from __future__ import annotations

import argparse
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "cell_tracking_matplotlib")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageSequence


@dataclass(frozen=True)
class Config:
    """All tunable image-processing parameters in one place."""

    denoise_radius: float = 1.0
    background_radius: float = 10.0
    minimum_contrast_threshold: int = 12
    opening_size: int = 3
    minimum_component_area: int = 20
    maximum_component_area: int = 500
    connectivity: int = 8


@dataclass
class FrameResult:
    crop: np.ndarray
    grayscale: np.ndarray
    denoised: np.ndarray
    contrast: np.ndarray
    mask: np.ndarray
    labels: np.ndarray
    components: list[dict[str, object]]
    threshold: int

    @property
    def count(self) -> int:
        return len(self.components)


def load_gif(path: Path) -> tuple[list[np.ndarray], tuple[int, int]]:
    """Load every GIF frame as RGB and verify the animation is consistent."""
    with Image.open(path) as image:
        if image.format != "GIF" or not getattr(image, "is_animated", False):
            raise ValueError(f"{path} is not an animated GIF")
        original_size = image.size
        expected_shape = (image.height, image.width, 3)
        frames = [
            np.asarray(frame.convert("RGB"), dtype=np.uint8)
            for frame in ImageSequence.Iterator(image)
        ]
        declared_frames = image.n_frames

    if len(frames) != declared_frames:
        raise RuntimeError("Pillow returned a different number of frames than GIF metadata")
    if any(frame.shape != expected_shape for frame in frames):
        raise ValueError("GIF frames do not all have the same dimensions")
    return frames, original_size


def crop_left_half(frame: np.ndarray) -> np.ndarray:
    """Return only the real microscopy image (never the right visualization)."""
    return frame[:, : frame.shape[1] // 2].copy()


def _as_gray(rgb: np.ndarray) -> np.ndarray:
    return np.asarray(Image.fromarray(rgb).convert("L"), dtype=np.uint8)


def preprocess_frame(crop: np.ndarray, config: Config) -> tuple[np.ndarray, ...]:
    """Denoise and remove slow illumination changes using local dark contrast.

    Bacteria are dark rods with bright halos. A broad Gaussian estimates the
    local background; subtracting a lightly smoothed image highlights dark rods
    while suppressing uneven illumination and most GIF compression texture.
    """
    grayscale = _as_gray(crop)
    gray_image = Image.fromarray(grayscale)
    denoised = np.asarray(
        gray_image.filter(ImageFilter.GaussianBlur(config.denoise_radius)),
        dtype=np.float32,
    )
    background = np.asarray(
        gray_image.filter(ImageFilter.GaussianBlur(config.background_radius)),
        dtype=np.float32,
    )
    contrast = np.clip(background - denoised, 0, 255).astype(np.uint8)
    return grayscale, denoised.astype(np.uint8), contrast


def otsu_threshold(image: np.ndarray) -> int:
    """Compute Otsu's global threshold for an 8-bit single-channel image."""
    histogram = np.bincount(image.ravel(), minlength=256).astype(np.float64)
    probabilities = histogram / histogram.sum()
    weights = np.cumsum(probabilities)
    means = np.cumsum(probabilities * np.arange(256))
    total_mean = means[-1]
    denominator = weights * (1.0 - weights)
    score = (total_mean * weights - means) ** 2 / np.maximum(denominator, 1e-12)
    score[(weights <= 0) | (weights >= 1)] = -1
    return int(np.argmax(score))


def _binary_morphology(mask: np.ndarray, operation: str, size: int) -> np.ndarray:
    if size < 1 or size % 2 == 0:
        raise ValueError("Morphology size must be a positive odd integer")
    if operation not in {"erode", "dilate"}:
        raise ValueError(f"Unknown morphology operation: {operation}")
    padding = size // 2
    padded = np.pad(mask, padding, mode="constant", constant_values=False)
    windows = np.lib.stride_tricks.sliding_window_view(padded, (size, size))
    if operation == "erode":
        return windows.all(axis=(-2, -1))
    return windows.any(axis=(-2, -1))


def segment_bacteria(contrast: np.ndarray, config: Config) -> tuple[np.ndarray, int]:
    """Threshold local dark contrast and remove isolated pixel-scale noise."""
    threshold = max(otsu_threshold(contrast), config.minimum_contrast_threshold)
    raw_mask = contrast >= threshold
    eroded = _binary_morphology(raw_mask, "erode", config.opening_size)
    opened = _binary_morphology(eroded, "dilate", config.opening_size)
    return opened, threshold


def connected_components(mask: np.ndarray, connectivity: int = 8) -> list[dict[str, object]]:
    """Find binary connected components without an external CV dependency."""
    if connectivity not in {4, 8}:
        raise ValueError("Connectivity must be 4 or 8")
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    if connectivity == 8:
        neighbors = [
            (dy, dx)
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            if (dy, dx) != (0, 0)
        ]
    else:
        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    components: list[dict[str, object]] = []
    for start_y, start_x in zip(*np.nonzero(mask)):
        if visited[start_y, start_x]:
            continue
        stack = [(int(start_y), int(start_x))]
        visited[start_y, start_x] = True
        pixels: list[tuple[int, int]] = []
        while stack:
            y, x = stack.pop()
            pixels.append((y, x))
            for dy, dx in neighbors:
                next_y, next_x = y + dy, x + dx
                if (
                    0 <= next_y < height
                    and 0 <= next_x < width
                    and mask[next_y, next_x]
                    and not visited[next_y, next_x]
                ):
                    visited[next_y, next_x] = True
                    stack.append((next_y, next_x))

        ys = np.fromiter((pixel[0] for pixel in pixels), dtype=np.int32)
        xs = np.fromiter((pixel[1] for pixel in pixels), dtype=np.int32)
        components.append(
            {
                "area": len(pixels),
                "bbox": (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())),
                "pixels": pixels,
            }
        )
    return components


def count_components(
    mask: np.ndarray, config: Config
) -> tuple[np.ndarray, list[dict[str, object]]]:
    """Area-filter components and return a labeled image plus retained objects."""
    all_components = connected_components(mask, config.connectivity)
    retained = [
        component
        for component in all_components
        if config.minimum_component_area
        <= int(component["area"])
        <= config.maximum_component_area
    ]
    labels = np.zeros(mask.shape, dtype=np.int32)
    for label, component in enumerate(retained, start=1):
        for y, x in component["pixels"]:  # type: ignore[union-attr]
            labels[y, x] = label
    return labels, retained


def process_frame(frame: np.ndarray, config: Config) -> FrameResult:
    crop = crop_left_half(frame)
    grayscale, denoised, contrast = preprocess_frame(crop, config)
    mask, threshold = segment_bacteria(contrast, config)
    labels, components = count_components(mask, config)
    return FrameResult(
        crop=crop,
        grayscale=grayscale,
        denoised=denoised,
        contrast=contrast,
        mask=mask,
        labels=labels,
        components=components,
        threshold=threshold,
    )


def process_all_frames(frames: Iterable[np.ndarray], config: Config) -> list[FrameResult]:
    return [process_frame(frame, config) for frame in frames]


def save_counts(counts: list[int], path: Path) -> None:
    """Write exactly one base-10 integer per frame."""
    path.write_text("\n".join(str(count) for count in counts) + "\n", encoding="ascii")


def visualize_detection(result: FrameResult) -> np.ndarray:
    overlay = Image.fromarray(result.crop.copy())
    draw = ImageDraw.Draw(overlay)
    for component in result.components:
        x0, y0, x1, y1 = component["bbox"]  # type: ignore[misc]
        draw.rectangle((x0, y0, x1, y1), outline=(255, 55, 55), width=1)
    draw.rectangle((3, 3, 91, 21), fill=(0, 0, 0))
    draw.text((7, 6), f"count = {result.count}", fill=(255, 255, 0))
    return np.asarray(overlay)


def save_sample_figures(
    results: list[FrameResult], output_dir: Path, sample_indices: dict[str, int]
) -> None:
    for name, index in sample_indices.items():
        result = results[index]
        Image.fromarray(result.crop).save(output_dir / f"frame_{name}.png")

        fig, axes = plt.subplots(1, 4, figsize=(14, 3.4))
        panels = [
            (result.crop, "Microscopy crop", None),
            (result.grayscale, "Grayscale", "gray"),
            (result.mask, f"Binary mask (t={result.threshold})", "gray"),
            (visualize_detection(result), f"Components: {result.count}", None),
        ]
        for axis, (image, title, cmap) in zip(axes, panels):
            axis.imshow(image, cmap=cmap)
            axis.set_title(title)
            axis.axis("off")
        fig.suptitle(f"Frame {index} (zero-based)")
        fig.tight_layout()
        fig.savefig(output_dir / f"frame_{name}_pipeline.png", dpi=180)
        plt.close(fig)


def plot_count_curve(counts: list[int], output_path: Path) -> None:
    frame_numbers = np.arange(len(counts))
    fig, axis = plt.subplots(figsize=(8, 4.5))
    axis.plot(frame_numbers, counts, marker="o", markersize=3, linewidth=1.5)
    axis.set(xlabel="Frame index (zero-based)", ylabel="Estimated bacteria count")
    axis.set_title("Estimated bacteria count over time")
    axis.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def save_anomaly_figure(
    results: list[FrameResult], counts: list[int], output_path: Path, number: int = 5
) -> list[tuple[int, int]]:
    differences = np.diff(counts)
    ranked = sorted(
        ((index + 1, int(change)) for index, change in enumerate(differences)),
        key=lambda item: (-abs(item[1]), item[0]),
    )[: min(number, len(differences))]
    fig, axes = plt.subplots(1, len(ranked), figsize=(3.2 * len(ranked), 3.1))
    axes = np.atleast_1d(axes)
    for axis, (index, change) in zip(axes, ranked):
        axis.imshow(visualize_detection(results[index]))
        axis.set_title(f"frame {index}\nchange {change:+d}")
        axis.axis("off")
    fig.suptitle("Largest adjacent-frame count changes")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return ranked


def validate_counts(path: Path, expected_frames: int) -> list[int]:
    text = path.read_text(encoding="ascii")
    lines = text.splitlines()
    if len(lines) != expected_frames:
        raise AssertionError(f"Expected {expected_frames} lines, found {len(lines)}")
    if any(not line.isdigit() for line in lines):
        raise AssertionError("counts.txt contains a blank or non-integer line")
    return [int(line) for line in lines]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("bacteria-animation.gif"))
    parser.add_argument("--output", type=Path, default=Path("counts.txt"))
    parser.add_argument("--figures", type=Path, default=Path("figures"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Config()
    frames, original_size = load_gif(args.input)
    print(f"number of frames: {len(frames)}")
    print(f"frame size: {original_size}")
    print(f"array shape: {frames[0].shape}")
    print(f"all frame shapes consistent: {all(f.shape == frames[0].shape for f in frames)}")

    results = process_all_frames(frames, config)
    counts = [result.count for result in results]
    assert len(counts) == len(frames)

    args.figures.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_counts(counts, args.output)
    validated_counts = validate_counts(args.output, len(frames))

    sample_indices = {"first": 0, "middle": len(frames) // 2, "last": len(frames) - 1}
    save_sample_figures(results, args.figures, sample_indices)
    plot_count_curve(counts, args.figures / "count_over_time.png")
    anomalies = save_anomaly_figure(
        results, counts, args.figures / "largest_count_changes.png"
    )

    print(f"counts: {validated_counts}")
    print(f"counts.txt lines: {len(validated_counts)}")
    print(f"minimum / maximum count: {min(counts)} / {max(counts)}")
    print("largest adjacent changes (destination frame, change):")
    for frame_index, change in anomalies:
        print(f"  frame {frame_index} (line {frame_index + 1}): {change:+d}")
    print(f"figures directory: {args.figures.resolve()}")


if __name__ == "__main__":
    main()
