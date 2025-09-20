# Radial Length Helper (WAN) — ComfyUI Custom Node

A tiny helper node for **WAN + RadialAttention** workflows. It snaps **Width / Height / Length** to valid values and shows a compact list of valid temporal lengths.

- **Models:** WAN 14B (stride **/16**) and WAN 5B (stride **/32**)
- **Inputs:** `model_kind`, `width`, `height`, `length`
- **Outputs:** `L_snapped`, `W_out`, `H_out`
- **UI:** compact readout with snapped spatial, snapped length, and **valid L** in **1..200** (max 4 rows, ellipsis if long)
- **Optional:** a frontend **JS overlay** for live, in-node updates while scrubbing (10px font)

---


## What the node does

- Snaps **Width/Height** to the **nearest** multiple of the model’s stride  
  (14B → /16, 5B → /32).
- Computes the temporal congruence so `tokens % 128 == 0`, where  
  `tokens = (W/stride) * (H/stride) * ((L+3)/4)` with integer `(L+3)/4`.
- Snaps **Length** `L` to the **nearest** valid value from that progression.
- Displays a compact readout in the node (and **live** if overlay is installed):
  - `spatial: W_in×H_in → W×H (/ stride)`
  - `L snapped: …`
  - `valid L (1..200): N vals` followed by up to 4 wrapped rows (ellipsis in the middle if long)

---

## Math details (reference)

- `stride = 16` for **WAN 14B**, `stride = 32` for **WAN 5B**.
- `A = (W/stride) * (H/stride)`.
- `tokens = A * T'` where `T' = (L+3)/4` must be an integer.
- We want `tokens % 128 == 0` → an arithmetic progression on `L`:
  - `g = gcd(128, A)`
  - `m = 4 * (128 / g)`
  - `r = (m - 3) mod m`
  - **Valid lengths:** `L ≡ r (mod m)`
- The node snaps the requested `L` to the **nearest** valid value.

---

##  Example wiring

```
[Radial Length Helper (WAN)]
   ├─ L_snapped  →  [EmptyHunyuanLatentVideo.length]
   ├─ W_out      →  [EmptyHunyuanLatentVideo.width]
   └─ H_out      →  [EmptyHunyuanLatentVideo.height]
```

---

##  Version notes

- Works with **ComfyUI Windows Portable** (Python embedded ok).  
- Independent of torch/CUDA; the node itself has no native deps.  
- Overlay uses Comfy’s `app.registerExtension` hook (no extra packages).

---

##  License & credits

- MIT (or your preferred permissive license).  
- Thanks to the **EA Motion Bias** node for the UX pattern (live overlay, compact readout).
