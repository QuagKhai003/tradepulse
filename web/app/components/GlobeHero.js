"use client";
/**
 * GlobeHero.js — client wrapper for the 3D globe (dynamic ssr:false) + a CSS intro.
 * @context  Loads GlobeInner only in the browser (three.js/window). A pure-CSS fade+scale reveal on
 *           mount (no motion lib) keeps the initial bundle lean.
 * @limits   Client island. All heavy WebGL lives in GlobeInner.
 * @affects  Placed in the hero on page.js.
 */
import dynamic from "next/dynamic";

const GlobeInner = dynamic(() => import("./GlobeInner.js"), {
  ssr: false,
  loading: () => <div className="globe-loading" aria-hidden />,
});

export default function GlobeHero(props) {
  return (
    <div className="globe-mount globe-intro">
      <GlobeInner {...props} />
    </div>
  );
}
