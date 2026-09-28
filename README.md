# Cell Tracking Challenge: Classical CV Baseline

## Project goal

This project automatically estimates the number of bacteria in every frame of
`bacteria-animation.gif`. It uses **only the left half** of each frame, which is
the real microscopy image. The right-hand tracking visualization is never used
for detection or counting.

## Environment

- Python 3.10 or newer
- Pillow
- NumPy
- Matplotlib

Install the dependencies with:

```bash
python3 -m pip install Pillow numpy matplotlib
```

## Run

From this directory:

```bash
python3 cell_count.py
```

Optional paths can be supplied with `--input`, `--output`, and `--figures`.
Running the default command is deterministic and regenerates all result files.

After generating the figures, build the PDF write-up with:

```bash
python3 generate_writeup_pdf.py
```

## Input

- `bacteria-animation.gif`: animated GIF with microscopy on the left and a
  pre-existing visualization on the right.

## Outputs

- `counts.txt`: exactly one integer per GIF frame, with no header or frame IDs.
- `figures/frame_{first,middle,last}.png`: three raw left-half crops.
- `figures/frame_{first,middle,last}_pipeline.png`: grayscale, mask, and
  component diagnostics for the same frames.
- `figures/count_over_time.png`: estimated count against frame index.
- `figures/largest_count_changes.png`: frames with the largest adjacent jumps.
- `output/pdf/cell_tracking_writeup.pdf`: formatted five-page research report.

## Algorithm overview

1. Load every GIF frame and crop the left half.
2. Convert the crop to grayscale and apply light Gaussian denoising.
3. Estimate the slowly varying background with a wider Gaussian blur.
4. Subtract the denoised image from the background. This emphasizes the dark
   rod-shaped cells while reducing uneven illumination and compression texture.
5. Apply an automatic Otsu threshold and a 3x3 morphological opening.
6. Find 8-connected components and retain components in a plausible area range.
7. Use the number of retained components as the frame's estimate.

All parameters are centralized in the `Config` dataclass in `cell_count.py`.
No frame-specific counts or corrections are hard-coded.

## Known limitations

There is no manual ground truth, so these estimates should not be interpreted as
measured accuracy. Touching bacteria can merge into one component and faint
bacteria can fall below the threshold. Conversely, a fragmented cell can be
counted more than once. The current images retain good separation between most
dark cell cores, so watershed splitting is not enabled by default; adding it
without ground truth could introduce more false splits than it fixes.
