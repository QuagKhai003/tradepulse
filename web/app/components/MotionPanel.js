/**
 * MotionPanel.js — slide/fade-in wrapper for the overlay panels (pure CSS, no motion lib).
 * @context  Wraps a server panel so it eases in from its side on load; reduced-motion handled globally.
 * @limits   Presentation only.
 * @affects  Wraps TopCountries + GlobalFeed on page.js.
 */
export default function MotionPanel({ children, className = "", from = "left", delay = 0 }) {
  return (
    <aside className={`${className} mpanel mpanel-${from}`} style={{ animationDelay: `${delay}s` }}>
      {children}
    </aside>
  );
}
