/**
 * WorldMap.js — SSR world choropleth, all countries, colored by the chosen flow's signal (plan §7.1).
 * @context  Server component. Colours every country by its export OR import signal band for the
 *           selected product; tooltip shows both flows. The hero of the app.
 * @done     Natural-Earth projection over world-atlas; reporter code -> world-atlas ISO id with a
 *           few Comtrade-specific overrides; neutral fill when a country has no data.
 * @limits   Presentation only; band colours from lib/format. No client JS.
 * @affects  Rendered by page.js; reads snapshot.countries + a metric ('exp'|'imp').
 */
import { geoNaturalEarth1, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import worldData from "world-atlas/countries-110m.json";
import { bandColor, fmtUSD, MAP_NEUTRAL } from "../lib/format.js";

const W = 960, H = 460;
// Comtrade reporterCode -> world-atlas numeric id where they differ from M49.
const OVERRIDE = { 842: 840, 251: 250, 757: 756, 579: 578, 699: 356, 490: 158, 97: 0 };
const norm = (v) => String(Number(v));               // strip leading zeros both sides

export default function WorldMap({ countries, metric, lang }) {
  const fc = feature(worldData, worldData.objects.countries);
  const projection = geoNaturalEarth1().fitSize([W, H], fc);
  const pathGen = geoPath(projection);

  const byId = {};
  for (const c of countries) {
    if (!c[metric]) continue;
    byId[norm(OVERRIDE[c.code] ?? c.code)] = c;
  }

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="worldmap" role="img" aria-label="World trade signal map">
      {fc.features.map((f) => {
        const c = byId[norm(f.id)];
        const slot = c && c[metric];
        const fill = slot ? bandColor(slot.band, slot.direction) : MAP_NEUTRAL;
        const d = pathGen(f);
        if (!d) return null;
        const nm = c ? (lang === "en" ? c.name_en : c.name_vi) : f.properties?.name;
        const tip = c
          ? `${nm} — ${lang === "en" ? "exp" : "XK"} ${fmtUSD(c.exp?.value_usd)} · ${lang === "en" ? "imp" : "NK"} ${fmtUSD(c.imp?.value_usd)}`
          : nm;
        return (
          <path key={f.id} d={d} fill={fill}
                stroke={slot ? "#0f172a" : "#d7dee8"} strokeWidth={slot ? 0.6 : 0.3}>
            <title>{tip}</title>
          </path>
        );
      })}
    </svg>
  );
}
