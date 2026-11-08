"""Figure 1 (manuscript) - reproducible corrections applied to the original raster artwork.

The repository contains no vector source for fig1.png (only the 1672x941 raster), so the figure is
corrected in place: the original is upscaled 2x (LANCZOS) and every changed label, equation and box is
redrawn on top of it.  All other pixels (icons, colours, arrows, layout) are the original artwork.

usage (from the repository root):
    python -I FINAL_CORRECTED_FIGURES/make_fig1_corrections.py manuscript/images/fig1.png FINAL_CORRECTED_FIGURES/fig1.png

Every change is listed in FINAL_CORRECTED_FIGURES/FIGURE_CHANGELOG.md; each block below is labelled
with the changelog item number [F1-xx].
Verified against the code: src_v2/experiment.py (round loop), src/recovery.py, src/aggregation.py,
src/privacy.py (capped_normalized_weights), src/server.py (apply_update).
"""
import io
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

matplotlib.rcParams["mathtext.fontset"] = "stix"
S = 2                      # working scale (output = 2x the original pixel grid)
EXTRA_H = 66               # [F1-17] extra rows (original pixels) for the branch note at the bottom

src = Image.open(sys.argv[1]).convert("RGB")
W, H = src.size
A = np.array(src).astype(int)
im = Image.new("RGB", (W * S, (H + EXTRA_H) * S), (255, 255, 255))
im.paste(src.resize((W * S, H * S), Image.LANCZOS), (0, 0))
ORIG2X = im.copy()


# ------------------------------------------------------------------ helpers (coordinates in ORIGINAL pixels)
def bg(box):
    x0, y0, x1, y1 = box
    p = A[y0:y1, x0:x1].reshape(-1, 3)
    lum = p.mean(1)
    return tuple(int(v) for v in np.median(p[lum > np.percentile(lum, 60)], 0))


def fg(box):
    x0, y0, x1, y1 = box
    p = A[y0:y1, x0:x1].reshape(-1, 3)
    lum = p.mean(1)
    return "#%02x%02x%02x" % tuple(int(v) for v in np.median(p[lum < np.percentile(lum, 4)], 0))


def render(s, px, color, weight="normal", family="Inter"):
    fig = plt.figure(figsize=(0.01, 0.01), dpi=72)
    fig.text(0, 0, s, fontsize=px * S, color=color, fontweight=weight, family=family)
    buf = io.BytesIO()
    fig.savefig(buf, transparent=True, bbox_inches="tight", pad_inches=0.01, dpi=72)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


def hcat(parts, gap=0):
    h = max(p.height for p in parts)
    out = Image.new("RGBA", (sum(p.width for p in parts) + gap * (len(parts) - 1), h), (0, 0, 0, 0))
    x = 0
    for p in parts:
        out.paste(p, (x, h - p.height), p)       # bottom-aligned (same font size -> same baseline)
        x += p.width + gap
    return out


def clear(box, color=None):
    c = color or bg(box)
    x0, y0, x1, y1 = box
    im.paste(c, (x0 * S, y0 * S, x1 * S, y1 * S))
    return c


def put(img, box, align="center"):
    x0, y0, x1, y1 = [v * S for v in box]
    bw = x1 - x0
    if img.width > bw:
        r = bw / img.width
        img = img.resize((int(img.width * r), int(img.height * r)), Image.LANCZOS)
    y = y0 + ((y1 - y0) - img.height) // 2
    x = x0 + (bw - img.width) // 2 if align == "center" else x0
    im.paste(img, (x, y), img)
    return img.width / S


def lines(texts, box, px, color, weight="normal", gap=1.25, align="center"):
    x0, y0, x1, y1 = box
    hstep = int(px * gap)
    ystart = y0 + ((y1 - y0) - hstep * len(texts)) // 2
    for k, t in enumerate(texts):
        put(render(t, px, color, weight), (x0, ystart + k * hstep, x1, ystart + (k + 1) * hstep), align=align)


def paste_orig(crop_box, at_xy):
    x0, y0, x1, y1 = [v * S for v in crop_box]
    piece = ORIG2X.crop((x0, y0, x1, y1))
    im.paste(piece, (at_xy[0] * S, at_xy[1] * S))


def pill(box, text, px, fill, color="white", weight="bold"):
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = [v * S for v in box]
    d.rounded_rectangle((x0, y0, x1, y1), radius=(y1 - y0) // 2, fill=fill)
    put(render(text, px, color, weight), box)


# colours sampled from the original artwork
PURPLE_T = fg((935, 455, 1125, 475))          # Stage-3 box titles
BODY = fg((930, 488, 1110, 528))              # Stage-3 body text
RED_T = fg((1380, 207, 1520, 228))            # Stage-4 box titles
ORANGE = (241, 111, 34)                       # Stage-4 accent (arrows / "Optional" chip border)

# ================================================================== Stage 1
# [F1-01] composite path score -> Eq. (1)
box = (158, 640, 428, 709); col = fg(box); clear(box)
put(render(r"$R_{i,p}=\lambda_L\hat{L}_{i,p}+\lambda_S\hat{S}_{i,p}+\lambda_Q\hat{Q}_{i,p}$", 21, col), (158, 640, 428, 683))
put(render(r"$\lambda_L+\lambda_S+\lambda_Q=1\;\;(0.4/0.3/0.3)$", 15, col), (158, 683, 428, 707))
# [F1-02] indicator symbols -> normalised path scores of Eq. (1)
for b, sym in [((62, 316, 104, 344), r"$\hat{L}_{i,p}$"), ((163, 323, 207, 346), r"$\hat{S}_{i,p}$"),
               ((260, 323, 304, 346), r"$\hat{Q}_{i,p}$")]:
    c = fg(b); clear(b); put(render(sym, 17, c), b)
# [F1-03] remove a_i under "Client Availability" (a_i denotes the aggregation weight in Eq. (9))
clear((364, 322, 400, 346))

# ================================================================== arrows / Stage 2
# [F1-04] returned updates are model differences, not the noisy aggregate
b = (1335, 33, 1400, 64); c = fg(b); clear(b)
put(render(r"$\{\Delta w_i^{(t)}\}$", 21, c), b, align="left")
# [F1-05] Stage 2: model differences, not parameters/gradients
b = (621, 539, 810, 563); c = fg(b); clear(b)
put(render(r"(model differences $\Delta w_i^{(t)}$)", 15, c), b, align="left")

# ================================================================== Stage 3
# [F1-06] header
b = (906, 131, 1190, 161); c = fg(b); clear(b)
put(render("Surrogate Imputation &", 21.5, c, "bold"), b)
# [F1-07] reorder: Received -> Failure detection -> Surrogate imputation -> Robust filtering (MAD)
#         (reference implementation: surrogates are built from the received real updates, then MAD
#          filters real + imputed updates; src_v2/experiment.py, surrogate_handling == "reference")
PANEL = bg((870, 549, 1010, 571))
MAD_CROP = (856, 438, 1190, 548)     # MAD box, border at y 441..547 (stops before the old arrow)
SUR_CROP = (856, 571, 1190, 697)     # surrogate box, border at y 574..693
ARROW = (1012, 549, 1043, 572)
clear((852, 437, 1194, 698), PANEL)
paste_orig(SUR_CROP, (856, 438))     # surrogate box -> border y 441..560
paste_orig(ARROW, (1012, 561))       # arrow 561..584
paste_orig(MAD_CROP, (856, 584))     # MAD box -> border y 587..693
clear((852, 694, 1194, 699), PANEL)  # remove any residue below the moved box
paste_orig((981, 545, 1011, 548), (1012, 691))   # re-draw the MAD box bottom edge where the old arrow joined it
# [F1-08] surrogate box: title + body (squares icon removed to give the text room)
INNER_SUR = bg((960, 606, 1100, 613))   # original surrogate-box interior
b = (900, 447, 1150, 472); clear(b, INNER_SUR)
put(render("Surrogate Imputation", 17.5, PURPLE_T, "bold"), b)
clear((922, 476, 1186, 554), INNER_SUR)
lines(["Coordinate-wise median surrogate", "for missing updates (when at least", "two real updates are available)"],
      (925, 478, 1186, 552), 14.5, BODY, gap=1.32, align="left")
# [F1-09] MAD box body
INNER_MAD = bg((960, 478, 1100, 486))   # original MAD-box interior
clear((924, 626, 1113, 683), INNER_MAD)
lines(["Filter outliers among real", "and imputed updates"], (928, 627, 1113, 682), 15.5, BODY, gap=1.35, align="left")

# ================================================================== Stage 4
# [F1-10] header
b = (1290, 126, 1642, 194); c = fg((1300, 130, 1600, 190)); clear(b)
lines(["Server-Side Aggregation &", "Global Model Update"], b, 21.5, c, "bold", gap=1.5)
# [F1-11] clipping box: mark as central-Gaussian branch
INNER_CLIP = bg((1330, 245, 1380, 262))
pill((1512, 206, 1630, 227), "Gaussian branch", 12.5, ORANGE)
# [F1-12] aggregation box: title + equation with the applied uniform weights
INNER_AGG = bg((1323, 338, 1332, 365))   # box interior just left of the old equation
clear((1322, 295, 1630, 370), INNER_AGG)
put(render("Capped Aggregation", 18, RED_T, "bold"), (1322, 295, 1630, 316))
put(render("(central-Gaussian branch)", 13.5, RED_T), (1322, 316, 1630, 333))
put(render(r"$u^{(t)}={\sum}_{i\in\mathcal{K}_t}a_i\,\overline{\Delta w}_i^{(t)},\quad a_i=1/|\mathcal{K}_t|$", 19, "#222222"),
    (1322, 334, 1630, 370))
# [F1-13] Gaussian perturbation: aggregate before noise is u, noise scale includes Delta_2
b = (1314, 447, 1634, 482); c = fg((1314, 447, 1450, 482)); clear(b)
put(render(r"$\tilde{u}^{(t)}=u^{(t)}+z^{(t)},\;z^{(t)}\sim\mathcal{N}(0,\sigma_{\mathrm{DP}}^{2}(\Delta_2^{(t)})^{2}I)$", 19, c), b, align="left")

# ================================================================== legend and banner
# [F1-14] legend: model update
b = (1051, 798, 1215, 820); c = fg(b); clear(b)
put(render(r"Model differences $\Delta w$", 13.5, c), b, align="left")
# [F1-15] legend: security & privacy
b = (1328, 798, 1560, 838); c = fg(b); clear(b)
lines(["Clipping + optional", "Gaussian perturbation"], b, 13.5, c, align="left", gap=1.35)
# [F1-16] banner sentence
b = (488, 864, 1405, 914); c = fg(b); clear(b)
lines(["The framework combines routing-aware client/path selection, surrogate imputation, robust filtering, and",
       "optional server-side Gaussian perturbation for federated intrusion detection."], b, 16.5, c, align="left", gap=1.4)

# ================================================================== [F1-17] branch note (new bottom row)
d = ImageDraw.Draw(im)
NOTE = (22, H + 6, 1650, H + EXTRA_H - 6)
border = tuple(int(v) for v in A[806, 22])          # legend-box border colour
d.rounded_rectangle([v * S for v in NOTE], radius=10 * S, fill=(255, 255, 255), outline=border, width=2 * S)
TXT = "#2b2b2b"
l1 = hcat([render("Central-Gaussian branch (optional): ", 15, TXT, "bold"),
           render(r"clipping $\rightarrow$ capped weights ($a_i=1/|\mathcal{K}_t|$ when 1–10 updates are retained) $\rightarrow$ Gaussian noise; "
                  r"$\hat{\varepsilon}$ is an accounting diagnostic, not certified differential privacy.", 15, TXT)])
l2 = hcat([render("Non-private reference: ", 15, TXT, "bold"),
           render(r"sample-size-weighted mean of retained, unclipped updates (no clipping, cap or noise; $\tilde{u}^{(t)}=u^{(t)}$).   ", 15, TXT),
           render("No valid positive-weight update: ", 15, TXT, "bold"),
           render(r"aggregation skipped; $w$ and $v$ unchanged; no noise.", 15, TXT)])
put(l1, (40, H + 10, 1635, H + 33), align="left")
put(l2, (40, H + 33, 1635, H + 56), align="left")

im.save(sys.argv[2], dpi=(600, 600))
print("saved", im.size)
