// Radial Length Helper (WAN) — minimal live overlay (10px font, compact list)
// Draws snapped W/H/L and valid lengths (1..200) as you edit the node's widgets.
// Display-only: backend outputs still come from the Python node when you run it.

import { app } from "/scripts/app.js";

(() => {
  // ---------- helpers ----------
  const gcd = (a, b) => {
    a = Math.abs(a | 0);
    b = Math.abs(b | 0);
    while (b) { const t = b; b = a % b; a = t; }
    return a;
  };
  const snapNearest = (v, base) =>
    Math.floor((Number(v) + Math.floor(base / 2)) / base) * base;

  const get = (node, name) => node.widgets?.find(w => w.name === name);
  const getNum = (node, name, def) => {
    const w = get(node, name);
    const n = Number(w?.value);
    return Number.isFinite(n) ? n : def;
  };
  const getStr = (node, name, def) => {
    const w = get(node, name);
    return (w && w.value != null) ? String(w.value) : def;
  };

  // Compact a long list into at most maxRows rows, 12 values per row, with an ellipsis row.
  function wrapValues(vals, cols = 12, maxRows = 4) {
    const rowsAll = [];
    for (let i = 0; i < vals.length; i += cols) {
      rowsAll.push(vals.slice(i, i + cols).join(", "));
    }
    if (rowsAll.length <= maxRows) return rowsAll;
    const head = Math.floor(maxRows / 2);
    const tail = maxRows - head - 1; // 1 row reserved for "…"
    const out = [];
    out.push(...rowsAll.slice(0, head));
    out.push("…");
    if (tail > 0) out.push(...rowsAll.slice(-tail));
    return out;
  }

  function computeLines(node) {
    // Read current widgets (basic node: model_kind, width, height, length)
    const model = getStr(node, "model_kind", "WAN 14B");
    const stride = (model === "WAN 5B") ? 32 : 16;

    const Win = getNum(node, "width", 1024);
    const Hin = getNum(node, "height", 576);
    const Lin = Math.max(1, getNum(node, "length", 61));

    // Snap spatial to model stride (nearest)
    const W = snapNearest(Win, stride);
    const H = snapNearest(Hin, stride);

    // Spatial tokens per T'
    const Wx = Math.floor(W / stride);
    const Hx = Math.floor(H / stride);
    const A  = Wx * Hx;

    // L congruence: require tokens%128==0 with T'=(L+3)/4 integer
    // g = gcd(128, A), m = 4 * (128 / g), r = (m - 3) % m
    const g = gcd(128, Math.max(1, A));
    const m = 4 * Math.floor(128 / g);
    const r = (m - 3) % m;

    // Snap L to nearest valid around Lin
    const off = ((Lin - r) % m + m) % m;
    const Lf  = Lin - off;
    const Lc  = Lin + ((m - off) % m);
    const Lsnap = Math.max(1, (Math.abs(Lin - Lf) <= Math.abs(Lc - Lin)) ? Lf : Lc);

    // Valid L values in 1..200
    const vals = [];
    let first = r;
    if (first < 1) {
      const k = Math.floor((1 - first + m - 1) / m);
      first += k * m;
    }
    for (let L = first; L <= 200; L += m) vals.push(L);

    const lines = [];
    lines.push(`spatial: ${Win}x${Hin} → ${W}x${H} (/ ${stride})`);
    lines.push(`L snapped: ${Lsnap}`);
    lines.push(`valid L (1..200): ${vals.length} vals`);
    lines.push(...wrapValues(vals, 12, 4));
    return lines;
  }

  function ensureSpacer(node) {
    let w = get(node, "__rlh_spacer__");
    if (!w) {
      w = node.addWidget("info", "", "");
      w.name = "__rlh_spacer__";
      w.serialize = false;
      w.draw = () => {};
      w.getHeight = () => node.__rlh_overlay_h || 0;
      w.computeSize = (width) => [width, node.__rlh_overlay_h || 0];
    }
    return w;
  }

  app.registerExtension({
    name: "wan.radial_length_helper.min.overlay.v2",
    nodeCreated(node) {
      if (node?.comfyClass !== "RadialLengthHelper") return;
      if (node.__rlh_min_installed) return;
      node.__rlh_min_installed = true;

      ensureSpacer(node);

      const padX = 8;
      const lineH = 12; // ~10pt font line height

      const prevDraw = node.onDrawForeground;
      node.onDrawForeground = function(ctx) {
        if (prevDraw) prevDraw.apply(this, arguments);
        const lines = computeLines(this);
        const overlayH = Math.min(300, lines.length * lineH) + 8;
        if (this.__rlh_overlay_h !== overlayH) {
          this.__rlh_overlay_h = overlayH;
          this.graph?.setDirtyCanvas(true, true);
        }
        const x = padX, y = this.size[1] - overlayH;

        ctx.save();
        ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace";
        ctx.shadowColor = "rgba(0,0,0,0.5)";
        ctx.shadowBlur = 2;

        let yy = y + 10;
        ctx.fillStyle = "#ffffff";
        for (const t of lines) {
          ctx.fillText(t, x, yy);
          yy += lineH;
        }
        ctx.restore();
      };

      // Repaint on any widget change (live updates)
      const prevChanged = node.onWidgetChanged;
      node.onWidgetChanged = function(w, i, prev) {
        const rv = prevChanged ? prevChanged.apply(this, arguments) : undefined;
        this.graph?.setDirtyCanvas(true, true);
        return rv;
      };

      // Repaint on load
      const prevCfg = node.onConfigure;
      node.onConfigure = function() {
        const rv = prevCfg ? prevCfg.apply(this, arguments) : undefined;
        setTimeout(() => this.graph?.setDirtyCanvas(true, true), 0);
        return rv;
      };
    },
  });
})();
