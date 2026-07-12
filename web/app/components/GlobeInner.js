"use client";
/**
 * GlobeInner.js — realistic interactive 3D signal globe (react-globe.gl / three.js WebGL).
 * @context  ONE photoreal Earth (blue-marble texture + relief bump + starfield) — the same imagery at
 *           every zoom, so the globe never changes appearance (zoom out = the original look). Country
 *           BORDERS (50m) appear only near country-level zoom, drawn as a single GL LineSegments buffer
 *           (one draw call, built lazily) and toggled by visibility — so the default globe stays smooth.
 *           Max anisotropic filtering keeps the texture sharp at grazing angles. A glowing signal POINT
 *           sits on every country with a signal (colour = direction, height = value); top movers pulse.
 *           Auto-rotates after idle; drag to spin; click to drill; hover for values. Client-only.
 * @limits   Client-only. Colours reuse signal semantics (vivid on the dark globe).
 * @affects  Rendered by GlobeHero; data from the snapshot (countries + metric).
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { BufferGeometry, Float32BufferAttribute, LineBasicMaterial, LineSegments } from "three";
import Globe from "react-globe.gl";
import { geoCentroid } from "d3-geo";
import { feature } from "topojson-client";
import worldData from "world-atlas/countries-110m.json";
import { fmtPct, fmtUSD } from "../lib/format.js";
// NB: the 50m border data (~0.75MB) is dynamically imported on first zoom-in (see updateBorders),
// so it stays OUT of the initial route compile + client bundle.

const OVERRIDE = { 842: 840, 251: 250, 757: 756, 579: 578, 699: 356, 490: 158, 97: 0 };
const norm = (v) => String(Number(v));
const UP = "#34d399", DOWN = "#fb7185", NEW = "#a78bfa";
const hue = (b, dir) => (b === "new" ? NEW : dir === "down" ? DOWN : UP);

// Country outlines drawn as ONE native GL LineSegments buffer (a single draw call for all ~98k
// segments) — react-globe.gl's pathsData builds a separate fat-line object per ring (1600+ draw
// calls) which is what made the globe lag. Built lazily on first zoom-in, toggled by .visible; only
// shown near country level (BORDER_IN/OUT) so the default globe renders none of it.
const BORDER_IN = 190, BORDER_OUT = 250;   // camera distance: show below IN, hide above OUT (hysteresis)
function toRings(features) {
  const rings = [];
  for (const f of features) {
    const g = f.geometry;
    if (!g) continue;
    const polys = g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
    for (const poly of polys) for (const ring of poly) rings.push(ring.map(([lng, lat]) => [lat, lng]));
  }
  return rings;
}

// All country outlines → ONE LineSegments buffer (single draw call). Vertices via getCoords so they
// sit exactly on the globe surface, aligned with the texture + signal points.
function buildLines(g, rings) {
  const pos = [];
  for (const ring of rings) {
    for (let i = 0; i < ring.length - 1; i++) {
      const a = g.getCoords(ring[i][0], ring[i][1], 0.003);
      const b = g.getCoords(ring[i + 1][0], ring[i + 1][1], 0.003);
      pos.push(a.x, a.y, a.z, b.x, b.y, b.z);
    }
  }
  const geo = new BufferGeometry();
  geo.setAttribute("position", new Float32BufferAttribute(pos, 3));
  const lines = new LineSegments(geo, new LineBasicMaterial({ color: 0xbcd0f8, transparent: true, opacity: 0.5, depthWrite: false }));
  lines.renderOrder = 1;
  g.scene().add(lines);
  return lines;
}

export default function GlobeInner({ countries, metric, hs, lang }) {
  const router = useRouter();
  const globeRef = useRef();
  const wrapRef = useRef();
  const linesRef = useRef(null);           // the single border LineSegments (built lazily, toggled)
  const buildingRef = useRef(false);       // guard against double-building during the async import
  const [size, setSize] = useState({ w: 800, h: 620 });

  // Sharpen the globe texture at grazing angles (max anisotropic filtering) — the most detail a single
  // texture can give without changing its appearance. react-globe.gl v2.38 exposes globeMaterial as a
  // PROP, not a ref method, so reach the material via the scene graph.
  const bumpAniso = () => {
    const g = globeRef.current;
    if (!g) return;
    try {
      const max = g.renderer().capabilities.getMaxAnisotropy();
      g.scene().traverse((o) => {
        const map = o.material && o.material.map;
        if (map && map.anisotropy !== undefined && map.anisotropy !== max) { map.anisotropy = max; map.needsUpdate = true; }
      });
    } catch {}
  };

  // Bump anisotropy once the base texture has loaded (onGlobeReady can fire before the map is set).
  useEffect(() => { const id = setTimeout(bumpAniso, 1200); return () => clearTimeout(id); }, []);

  const features = useMemo(() => feature(worldData, worldData.objects.countries).features, []);

  // Cleanup: drop the border geometry from the scene on unmount.
  useEffect(() => () => {
    const l = linesRef.current;
    if (l) { l.parent && l.parent.remove(l); l.geometry.dispose(); l.material.dispose(); linesRef.current = null; }
  }, []);
  const byId = useMemo(() => {
    const m = {};
    for (const c of countries) if (c[metric]) m[norm(OVERRIDE[c.code] ?? c.code)] = c;
    return m;
  }, [countries, metric]);

  const points = useMemo(() => {
    const out = [];
    for (const f of features) {
      const d = byId[norm(f.id)];
      const slot = d && d[metric];
      if (!slot || slot.band === "none") continue;
      const [lng, lat] = geoCentroid(f);
      if (!isFinite(lat) || !isFinite(lng)) continue;
      out.push({ lat, lng, code: d.code, name: lang === "en" ? d.name_en : d.name_vi,
                 band: slot.band, direction: slot.direction, val: slot.value_usd, yoy: slot.yoy_delta });
    }
    return out;
  }, [features, byId, metric, lang]);

  const maxVal = useMemo(() => Math.max(1, ...points.map((p) => p.val)), [points]);
  const rings = useMemo(
    () => [...points].sort((a, b) => Math.abs(b.yoy || 0) - Math.abs(a.yoy || 0)).slice(0, 10),
    [points]
  );

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    setSize({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const g = globeRef.current;
    if (!g) return;
    const c = g.controls();
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    c.autoRotate = false;                 // idle by default — only spins after 5s of no interaction
    c.autoRotateSpeed = 0.5;
    c.enableZoom = true; c.enablePan = false;
    c.minDistance = 120; c.maxDistance = 520;
    c.zoomSpeed = 0.8;
    g.pointOfView({ lat: 12, lng: 30, altitude: 1.6 }, 0);

    // Show borders only near country level; hide (→ original globe) when zoomed back out. Hysteresis
    // stops flicker. The 50m data is dynamically imported on the FIRST zoom-in (off the initial bundle),
    // built once into a single LineSegments, then just toggled by .visible (no React re-render).
    const updateBorders = async () => {
      const dist = typeof c.getDistance === "function" ? c.getDistance() : g.camera().position.length();
      const show = dist < BORDER_IN ? true : dist > BORDER_OUT ? false : null;
      if (show === null) return;
      if (show && !linesRef.current && !buildingRef.current) {
        buildingRef.current = true;
        try {
          const mod = await import("world-atlas/countries-50m.json");
          const g2 = globeRef.current;
          if (g2) linesRef.current = buildLines(g2, toRings(feature(mod.default, mod.default.objects.countries).features));
        } catch {}
      }
      if (linesRef.current) linesRef.current.visible = show;
    };

    let timer;
    const spinAfterIdle = () => { clearTimeout(timer); if (!reduced) timer = setTimeout(() => { c.autoRotate = true; }, 5000); };
    const stop = () => { clearTimeout(timer); c.autoRotate = false; };
    const onStart = () => stop();
    const onEnd = () => { spinAfterIdle(); updateBorders(); };
    const onWheel = () => { stop(); spinAfterIdle(); updateBorders(); };
    const wrap = wrapRef.current;
    c.addEventListener("start", onStart);
    c.addEventListener("end", onEnd);
    wrap && wrap.addEventListener("wheel", onWheel, { passive: true });
    spinAfterIdle();                      // begin idle countdown on load
    return () => {
      clearTimeout(timer);
      c.removeEventListener("start", onStart);
      c.removeEventListener("end", onEnd);
      wrap && wrap.removeEventListener("wheel", onWheel);
    };
  }, [size.w]);

  const label = (p) =>
    `<div class="globe-tip"><b>${p.name}</b><span>${fmtUSD(p.val)} · ${fmtPct(p.yoy)}</span></div>`;

  return (
    <div ref={wrapRef} className="globe-canvas">
      <Globe
        ref={globeRef}
        width={size.w}
        height={size.h}
        backgroundColor="rgba(0,0,0,0)"
        globeImageUrl="/textures/earth.jpg"
        bumpImageUrl="/textures/earth-topology.png"
        onGlobeReady={bumpAniso}
        showAtmosphere
        atmosphereColor="#7c9bff"
        atmosphereAltitude={0.2}
        pointsData={points}
        pointColor={(p) => hue(p.band, p.direction)}
        pointAltitude={(p) => 0.012 + 0.55 * Math.sqrt(p.val / maxVal)}
        pointRadius={0.55}
        pointResolution={16}
        pointLabel={label}
        onPointClick={(p) => router.push(`/country/${p.code}?hs=${hs}${lang === "en" ? "&lang=en" : ""}`)}
        ringsData={rings}
        ringColor={(r) => (t) => {
          const c = hue(r.band, r.direction);
          return `${c}${Math.round((1 - t) * 200).toString(16).padStart(2, "0")}`;
        }}
        ringMaxRadius={3.2}
        ringPropagationSpeed={1.4}
        ringRepeatPeriod={1300}
      />
    </div>
  );
}
