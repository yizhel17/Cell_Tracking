# Objective

Estimate the number of bacteria automatically in every frame of the supplied
animated GIF using a reproducible, interpretable computer-vision method.

# Dataset

`bacteria-animation.gif` is an animated GIF with 40 frames. Every full frame is
640 pixels wide by 240 pixels high and loads as an RGB array with shape
`(240, 640, 3)`. Only columns 0 through 319—the left half containing the real
microscopy image—are processed. The laboratory visualization on the right is
not examined for counts.

# Method

The script performs the following operations independently on every frame:

1. Crop the left half and convert it to 8-bit grayscale.
2. Apply a Gaussian blur with radius 1 pixel to suppress pixel-scale and GIF
   compression noise.
3. Estimate the local background with a Gaussian blur of radius 10 pixels.
4. Compute `background - denoised`. The bacteria are locally dark, so they have
   a strong positive response, while broad illumination variation is removed.
5. Select a threshold automatically with Otsu's method (with a conservative
   minimum response threshold of 12 gray levels).
6. Apply a 3x3 morphological opening to remove tiny isolated responses.
7. Label 8-connected components and retain areas from 20 through 500 pixels.
8. Report the number of retained components.

The three radius/size/area settings were selected after visually inspecting the
first, middle, and last microscopy crops and their intermediate masks. They are
global settings applied identically to all frames; no individual result was
manually edited. The broad background subtraction was chosen after observing
uneven illumination and low-level GIF texture in a direct grayscale threshold.

# Why This Method

A classical CV baseline is appropriate because the dataset is one short
animation, the bacteria have a consistent dark rod appearance, and the task is
counting rather than semantic recognition. The method is transparent, fast,
does not require labeled training data or a pretrained model, and exposes its
failure modes directly in the saved masks and overlays.

# Results

The complete run processes all 40 frames and writes one estimate per frame to
`counts.txt`. Counts range from 3 to 19. Selected zero-based frames are:

- Frame 0: 3
- Frame 20: 8
- Frame 39: 19

The full trend is saved in `figures/count_over_time.png`. It generally rises as
the colony grows, without enforcing monotonicity. The largest adjacent-frame
changes are visualized in `figures/largest_count_changes.png`, and detailed
pipeline images for frames 0, 20, and 39 are also saved in `figures/`.

This is a sanity check, not an accuracy measurement, because ground-truth cell
counts were not supplied.

# Failure Analysis

- **Noise:** Compression speckles and uneven illumination can produce dark
  pixels. Gaussian denoising, local background subtraction, opening, and the
  minimum-area filter remove most of them.
- **Touching cells / undercount:** Two cells whose dark cores touch can become
  one connected component. This risk increases as the colony becomes dense.
- **Low contrast / undercount:** A faint cell may not exceed Otsu's threshold,
  particularly during focus or illumination changes.
- **Fragmentation / overcount:** If a rod's response has a gap, its two pieces
  can survive as separate components. The current opening removes noise but
  intentionally avoids aggressive closing, which could merge adjacent cells.
- **Dense colony:** Late frames contain more contacts and overlaps, making a
  simple component count less reliable than it is in early frames.
- **Area filtering:** Very small faint cells can be discarded, while a very
  large merged group could exceed the maximum area and be discarded entirely.

# Limitations

There is no ground truth, so no accuracy percentage or claim of optimality is
made. Parameters were chosen on this animation and may not transfer unchanged
to different magnification, focus, contrast, or cell morphology. Connected
components count visible segmented objects; they do not establish cell identity
or track lineage through time.

# Possible Improvements

- Validate parameters against manually annotated sample frames.
- Split genuinely merged components with marker-controlled watershed after
  validating that it does not split single rods.
- Use temporal correspondence to distinguish real divisions from segmentation
  flicker while still reporting the raw per-frame evidence.
- With a larger labeled dataset, compare against learned instance segmentation.
- Extend the task from counting to true cell tracking and lineage assignment.

Watershed is not used in this baseline. The retained dark cores are mostly
separate, the count trend is stable, and there is no ground truth with which to
tune split markers. It is worth testing only after annotating dense late frames.

# References

Only documentation used while implementing this solution is listed:

1. Pillow, `ImageSequence` module:
   <https://pillow.readthedocs.io/en/stable/reference/ImageSequence.html>
2. Pillow, `ImageFilter` module and Gaussian blur:
   <https://pillow.readthedocs.io/en/stable/reference/ImageFilter.html>
3. NumPy, `sliding_window_view`:
   <https://numpy.org/doc/stable/reference/generated/numpy.lib.stride_tricks.sliding_window_view.html>
4. Matplotlib, `savefig`:
   <https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html>

The professor's published 2D-case paper was not used to construct this solution.
