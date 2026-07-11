"use client";
/**
 * GlobeInner.js — realistic interactive 3D signal globe (react-globe.gl / three.js WebGL).
 * @context  A photoreal Earth (blue-marble texture + relief bump + starfield) with a glowing signal
 *           POINT on every country that has a signal for the chosen product+flow — colour = direction,
 *           height = value. Top movers emit pulsing rings (the "pulse"). Auto-rotates; drag to spin;
 *           click a point to drill in; hover for values. Client-only (three/window safe here).
 * @limits   Client-only. Colours reuse signal semantics (vivid on the dark globe).
 * @affects  Rendered by GlobeHero; data from the snapshot (countries + metric).
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Globe from "react-globe.gl";
import { geoCentroid } from "d3-geo";
import { feature } from "topojson-client";
import worldData from "world-atlas/countries-110m.json";
import { fmtPct, fmtUSD } from "../lib/format.js";

const OVERRIDE = { 842: 840, 251: 250, 757: 756, 579: 578, 699: 356, 490: 158, 97: 0 };
const norm = (v) => String(Number(v));
const UP = "#34d399", DOWN = "#fb7185", NEW = "#a78bfa";
const hue = (b, dir) => (b === "new" ? NEW : dir === "down" ? DOWN : UP);

export default function GlobeInner({ countries, metric, hs, lang }) {
  const router = useRouter();
  const globeRef = useRef();
  const wrapRef = useRef();
  const hiResRef = useRef(false);          // guard: swap to the 8k texture at most once
  const [size, setSize] = useState({ w: 800, h: 620 });
  const [globeImg, setGlobeImg] = useState("/textures/earth.jpg");

  // Sharpen every globe texture at grazing angles (max anisotropic filtering). react-globe.gl v2.38
  // exposes globeMaterial as a PROP, not a ref method, so reach the material via the scene graph.
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

  // After the (base or 8k) texture swaps in, wait a beat for it to load, then bump anisotropy.
  useEffect(() => { const id = setTimeout(bumpAniso, 900); return () => clearTimeout(id); }, [globeImg]);

  const features = useMemo(() => feature(worldData, worldData.objects.countries).features, []);
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

    // Progressive detail: the 4k base is crisp from afar but soft up close. The first time the user
    // zooms past the threshold, lazily fetch the 8k texture and swap it into the globe material (with
    // max anisotropy so it stays sharp at grazing angles). Fetched once, on demand — initial load is
    // untouched (the 8k never downloads unless someone zooms in).
    const maybeHiRes = () => {
      if (hiResRef.current) return;
      const dist = typeof c.getDistance === "function" ? c.getDistance() : g.camera().position.length();
      if (dist > 230) return;
      hiResRef.current = true;
      // preload so the swap is flash-free, then hand the URL to react-globe.gl (it manages the map)
      const img = new Image();
      img.onload = () => setGlobeImg("/textures/earth-8k.jpg");
      img.src = "/textures/earth-8k.jpg";
    };

    let timer;
    const spinAfterIdle = () => { clearTimeout(timer); if (!reduced) timer = setTimeout(() => { c.autoRotate = true; }, 5000); };
    const stop = () => { clearTimeout(timer); c.autoRotate = false; };
    const onStart = () => stop();
    const onEnd = () => { spinAfterIdle(); maybeHiRes(); };
    const onWheel = () => { stop(); spinAfterIdle(); maybeHiRes(); };
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
        globeImageUrl={globeImg}
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
