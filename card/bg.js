// Full-bleed card background: a wall of slightly uneven panels, lit by blue and orange light.
// paintBackground({ gap, tile, tileAlt, lights: [{x, y, r, color, opacity}], vignette })
// render.py adds ?bleed to render with 3 mm (36 px) extra background on every side.
if (location.search.includes("bleed")) document.documentElement.classList.add("bleed");

function paintBackground(opts) {
  const NS = "http://www.w3.org/2000/svg";
  const W = 2480, H = 1748;
  const svg = document.querySelector("svg.bg");
  let seed = opts.seed || 11;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const el = (name, attrs, parent = svg) => {
    const e = document.createElementNS(NS, name);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    parent.appendChild(e);
    return e;
  };
  const defs = el("defs", {});

  el("rect", { x: -100, y: -100, width: W + 200, height: H + 200, fill: opts.gap });

  // Panels: 14 columns, a few split in half or slightly darker so the wall doesn't look like graph paper.
  const cols = 14, size = W / cols, rows = Math.ceil(H / size) + 1;
  const offY = (H - rows * size) / 2, gap = 7;
  for (let r = -1; r <= rows; r++) {
    for (let c = -1; c <= cols; c++) {
      const x = c * size, y = offY + r * size;
      const fill = rnd() < 0.28 ? opts.tileAlt : opts.tile;
      if (rnd() < 0.16) {
        const h = (size - gap) / 2 - gap / 2;
        el("rect", { x: x + gap / 2, y: y + gap / 2, width: size - gap, height: h, rx: 5, fill });
        el("rect", { x: x + gap / 2, y: y + gap / 2 + h + gap, width: size - gap, height: h, rx: 5, fill: opts.tile });
      } else {
        el("rect", { x: x + gap / 2, y: y + gap / 2, width: size - gap, height: size - gap, rx: 6, fill });
      }
    }
  }

  // Coloured light falling on the wall.
  opts.lights.forEach((l, i) => {
    const g = el("radialGradient", { id: `light${i}` }, defs);
    el("stop", { offset: 0, "stop-color": l.color, "stop-opacity": l.opacity }, g);
    el("stop", { offset: 0.45, "stop-color": l.color, "stop-opacity": l.opacity * 0.4 }, g);
    el("stop", { offset: 1, "stop-color": l.color, "stop-opacity": 0 }, g);
    el("ellipse", { cx: l.x, cy: l.y, rx: l.r, ry: l.ry || l.r, fill: `url(#light${i})` });
  });

  if (opts.vignette) {
    const v = el("radialGradient", { id: "vignette", cx: 0.5, cy: 0.45, r: 0.75 }, defs);
    el("stop", { offset: 0.55, "stop-color": "#000", "stop-opacity": 0 }, v);
    el("stop", { offset: 1, "stop-color": "#000", "stop-opacity": opts.vignette }, v);
    el("rect", { x: -100, y: -100, width: W + 200, height: H + 200, fill: "url(#vignette)" });
  }
}

// Centre of an element in card pixels.
function centerOf(id) {
  const r = document.getElementById(id).getBoundingClientRect();
  const card = document.querySelector(".card").getBoundingClientRect();
  return { x: r.left + r.width / 2 - card.left, y: r.top + r.height / 2 - card.top };
}
