"use client";
/**
 * SortMenu.js — compact sort dropdown for the signals feed (plan §7.1).
 * @context  Sort signals by severity (default), % change, value, or name. The menu is portalled to
 *           <body> with fixed positioning so the panel's overflow:hidden + backdrop-filter (a
 *           containing block) can't clip it. Client state; onChange lifts to the hero.
 * @limits   Presentation; onChange lifts to the hero.
 * @affects  Rendered in the signals panel header.
 */
import { useState, useRef } from "react";
import { createPortal } from "react-dom";

export default function SortMenu({ value, onChange, t }) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState(null);
  const btnRef = useRef(null);
  const opts = [
    ["name-asc", t.sortNameAsc], ["name-desc", t.sortNameDesc],
    ["change-desc", t.sortChangeUp], ["change-asc", t.sortChangeDown],
    ["value-desc", t.sortValueHigh], ["value-asc", t.sortValueLow],
  ];

  function toggle() {
    if (!open && btnRef.current) {
      const btn = btnRef.current.getBoundingClientRect();
      const panelEl = btnRef.current.closest(".glasscol") || btnRef.current.closest(".panel-col");
      const panel = panelEl ? panelEl.getBoundingClientRect() : btn;
      // sit the menu just LEFT of the panel (in the gap next to it), not layered over the feed
      const right = Math.round(window.innerWidth - panel.left + 10);
      const width = 236;
      const clamped = Math.min(right, window.innerWidth - width - 8); // keep on-screen
      setPos({ top: Math.round(btn.top), right: Math.max(8, clamped) });
    }
    setOpen((o) => !o);
  }

  return (
    <div className="sortm">
      <button ref={btnRef} type="button" className="sortm-btn" onClick={toggle}
              onBlur={() => setTimeout(() => setOpen(false), 160)} aria-expanded={open}>
        <span className="sortm-ic">⇅</span> {t.sort}
      </button>
      {open && pos && createPortal(
        <ul className="sortm-menu" style={{ position: "fixed", top: pos.top, right: pos.right }}>
          {opts.map(([v, l]) => (
            <li key={v}>
              <button type="button" className={`sortm-opt ${v === value ? "on" : ""}`}
                      onMouseDown={() => { onChange(v); setOpen(false); }}>{l}</button>
            </li>
          ))}
        </ul>,
        document.body,
      )}
    </div>
  );
}
