/* pgm-tooltip.js -- render P2/P5 (PGM) source as a hover preview.
 *
 * Drop this on a page and any element carrying PGM source gets a tooltip that
 * draws the actual bitmap when you point at it.  Two ways to mark an element:
 *
 *   <pre data-pgm>P2 ...</pre>        explicit: always treated as PGM
 *   <pre>P5 ...</pre>                 sniffed: any <pre> starting P1..P6
 *
 * Call PGM.scan() after the DOM loads (this file does it for you), or
 * PGM.attach(el) for one element, or PGM.parse(textOrBytes) to get pixels.
 *
 * Handles: P2 (ASCII gray) and P5 (binary gray), '#' comments, any maxval,
 * 8-bit samples.  Colour (P3/P6) and 16-bit are out of scope on purpose --
 * this is a preview for the grey formats the wiki actually uses.
 */
(function (global) {
  "use strict";

  // --- parsing ------------------------------------------------------------

  // A P5 raster is raw bytes, so callers that read it out of a DOM text node
  // must preserve byte values -- charCodeAt does, as long as nothing upstream
  // re-encoded it. We accept either a string (latin-1 bytes) or a Uint8Array.
  function toBytes(src) {
    if (src instanceof Uint8Array) return src;
    const b = new Uint8Array(src.length);
    for (let i = 0; i < src.length; i++) b[i] = src.charCodeAt(i) & 255;
    return b;
  }

  function parse(src) {
    const b = toBytes(src);
    let i = 0;
    const n = b.length;

    function skipWS() {
      while (i < n) {
        const c = b[i];
        if (c === 35) {                       // '#' -> comment to EOL
          while (i < n && b[i] !== 10) i++;
        } else if (c === 32 || c === 9 || c === 10 || c === 13) {
          i++;
        } else break;
      }
    }
    function token() {
      skipWS();
      let s = "";
      while (i < n) {
        const c = b[i];
        if (c === 32 || c === 9 || c === 10 || c === 13) break;
        s += String.fromCharCode(c);
        i++;
      }
      return s;
    }

    const magic = token();
    if (!/^P[1-6]$/.test(magic)) throw new Error("not a PNM (got " + JSON.stringify(magic) + ")");
    const kind = +magic[1];
    if (kind !== 2 && kind !== 5) throw new Error("only P2 and P5 (gray) supported, got " + magic);

    const w = +token(), h = +token(), maxval = +token();
    if (!(w > 0 && h > 0 && maxval > 0)) throw new Error("bad header dimensions");

    const px = new Uint8ClampedArray(w * h);

    if (kind === 2) {                          // ASCII samples
      for (let k = 0; k < w * h; k++) {
        const t = token();
        if (t === "") throw new Error("P2 raster ended early at pixel " + k);
        px[k] = Math.round((+t) * 255 / maxval);
      }
    } else {                                   // P5: one whitespace, then bytes
      i++;                                     // consume the single delimiter
      if (n - i < w * h) throw new Error("P5 raster short: " + (n - i) + " of " + (w * h) + " bytes");
      const scale = 255 / maxval;
      for (let k = 0; k < w * h; k++) px[k] = Math.round(b[i + k] * scale);
    }

    return { width: w, height: h, maxval: maxval, kind: kind, gray: px };
  }

  // --- rendering ----------------------------------------------------------

  function toCanvas(pgm, scale) {
    const c = document.createElement("canvas");
    c.width = pgm.width;
    c.height = pgm.height;
    const ctx = c.getContext("2d");
    const img = ctx.createImageData(pgm.width, pgm.height);
    for (let k = 0; k < pgm.gray.length; k++) {
      const v = pgm.gray[k], j = k * 4;
      img.data[j] = img.data[j + 1] = img.data[j + 2] = v;
      img.data[j + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    if (!scale || scale === 1) return c;

    const big = document.createElement("canvas");
    big.width = pgm.width * scale;
    big.height = pgm.height * scale;
    const bctx = big.getContext("2d");
    bctx.imageSmoothingEnabled = false;       // keep pixels crisp
    bctx.drawImage(c, 0, 0, big.width, big.height);
    return big;
  }

  // --- tooltip ------------------------------------------------------------

  let tip = null;
  function ensureTip() {
    if (tip) return tip;
    tip = document.createElement("div");
    tip.className = "pgm-tip";
    tip.setAttribute("role", "tooltip");
    document.body.appendChild(tip);
    return tip;
  }

  function fitScale(pgm, cap) {
    const c = cap || 256;
    const s = Math.max(1, Math.floor(c / Math.max(pgm.width, pgm.height)));
    return s;
  }

  function attach(el) {
    if (el.__pgmBound) return;
    el.__pgmBound = true;
    el.classList.add("pgm-src");

    let cache = null, failed = false;
    function build() {
      if (cache || failed) return;
      try {
        const pgm = parse(el.dataset.pgmSrc != null ? el.dataset.pgmSrc : el.textContent);
        const canvas = toCanvas(pgm, fitScale(pgm));
        cache = { pgm: pgm, canvas: canvas };
      } catch (e) {
        failed = true;
        cache = { error: e.message };
      }
    }

    function show(ev) {
      build();
      const t = ensureTip();
      t.innerHTML = "";
      if (cache.error) {
        t.classList.add("pgm-tip--err");
        t.textContent = "can't render: " + cache.error;
      } else {
        t.classList.remove("pgm-tip--err");
        // NB: cloneNode does not copy a canvas bitmap, so append the real one.
        // There is only ever one tooltip, so a single canvas per element is fine.
        t.appendChild(cache.canvas);
        const meta = document.createElement("div");
        meta.className = "pgm-tip__meta";
        meta.textContent = "P" + cache.pgm.kind + " \u00b7 " +
          cache.pgm.width + "\u00d7" + cache.pgm.height +
          " \u00b7 max " + cache.pgm.maxval;
        t.appendChild(meta);
      }
      t.style.display = "block";
      move(ev);
    }
    function move(ev) {
      if (!tip) return;
      const pad = 14;
      let x = ev.clientX + pad, y = ev.clientY + pad;
      const r = tip.getBoundingClientRect();
      if (x + r.width > innerWidth) x = ev.clientX - pad - r.width;
      if (y + r.height > innerHeight) y = ev.clientY - pad - r.height;
      tip.style.left = Math.max(4, x) + "px";
      tip.style.top = Math.max(4, y) + "px";
    }
    function hide() { if (tip) tip.style.display = "none"; }

    el.addEventListener("mouseenter", show);
    el.addEventListener("mousemove", move);
    el.addEventListener("mouseleave", hide);
    // keyboard access: focusable, preview on focus
    if (!el.hasAttribute("tabindex")) el.tabIndex = 0;
    el.addEventListener("focus", function (e) {
      const r = el.getBoundingClientRect();
      show({ clientX: r.right, clientY: r.top });
    });
    el.addEventListener("blur", hide);
  }

  function looksLikePGM(text) {
    return /^\s*P[1-6]\s/.test(text.slice(0, 40));
  }

  function scan(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-pgm]").forEach(attach);
    scope.querySelectorAll("pre").forEach(function (pre) {
      if (!pre.hasAttribute("data-pgm") && looksLikePGM(pre.textContent)) attach(pre);
    });
  }

  const PGM = { parse: parse, toCanvas: toCanvas, attach: attach, scan: scan };
  global.PGM = PGM;
  if (typeof module !== "undefined" && module.exports) module.exports = PGM;

  if (typeof document !== "undefined") {
    if (document.readyState === "loading")
      document.addEventListener("DOMContentLoaded", function () { scan(); });
    else scan();
  }
})(typeof window !== "undefined" ? window : this);
