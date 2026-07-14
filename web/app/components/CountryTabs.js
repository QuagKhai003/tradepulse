"use client";
/**
 * CountryTabs.js — the three party views of one product IN one country: buyers, sellers, past orders.
 * @context  The globe answers "where is demand moving" — signals only. The moment you click a country
 *           you are asking about that market specifically, so the parties live HERE, as tabs.
 *           Each tab is scoped to this country first: buyers whose organisation is here, sellers based
 *           here, orders this country took part in — with the product-wide rest available below.
 * @warn     The tabs ALWAYS render, for every product and every country. The layout is a constant; only
 *           its contents change. A tab that disappears when empty makes the page a different page and
 *           leaves the user wondering what they did wrong — so an empty tab instead says WHY it is
 *           empty (no coverage here / aggregate heading / nothing on record yet).
 * @golden   Inform, never match — the lists themselves carry the rule; this only arranges them.
 * @limits   Presentation + tab state.
 * @affects  Rendered by country/[code]/page.js; wraps TenderList / SellerList / OrderList.
 */
import { useState } from "react";
import TenderList from "./TenderList.js";
import SellerList from "./SellerList.js";
import OrderList from "./OrderList.js";

export default function CountryTabs({ tHere = [], tElse = [], sellers = [], orders = [],
                                      product, country, cpv, hs, lang, t }) {
  const [tab, setTab] = useState("buyers");
  // "All products" (HS TOTAL) is an aggregate of every heading, not a good anyone can tender for — so
  // it has no CPV and never will. Say that, rather than showing an empty list that looks like a bug.
  const isAggregate = hs === "TOTAL";
  const noCoverage = !isAggregate && !cpv;

  const tabs = [
    { v: "buyers", label: t.tabBuyers, n: tHere.length + tElse.length },
    { v: "sellers", label: t.tabSellers, n: sellers.length },
    { v: "orders", label: t.tabOrders, n: orders.length },
  ];

  const why = isAggregate ? t.aggregateNote : (noCoverage ? t.noCpvNote : null);

  return (
    <section className="panel tender-sec">
      <div className="ctabs">
        {tabs.map((x) => (
          <button key={x.v} type="button" className={`ctab ${tab === x.v ? "on" : ""}`}
                  onClick={() => setTab(x.v)}>
            {x.label} <b className="num">{x.n}</b>
          </button>
        ))}
      </div>

      {why && <p className="muted tender-note">{why}</p>}

      {!why && tab === "buyers" && (
        <>
          {tHere.length > 0 ? (
            <>
              <h3 className="tender-sub">{t.tendersHere} {country} <span className="muted">({tHere.length})</span></h3>
              <TenderList tenders={tHere} lang={lang} t={t} product={product} />
            </>
          ) : (
            <p className="muted tender-note">{t.tendersNoneHere} {country}. {t.tendersElsewhereNote}</p>
          )}
          {tElse.length > 0 && (
            <>
              <h3 className="tender-sub">{t.tendersElsewhere} <span className="muted">({tElse.length})</span></h3>
              <TenderList tenders={tElse} lang={lang} t={t} product={product} cpv={cpv} />
            </>
          )}
          {tHere.length === 0 && tElse.length === 0 && (
            <p className="muted tender-note">{t.tendersNone}</p>
          )}
        </>
      )}

      {!why && tab === "sellers" && (
        sellers.length > 0
          ? <SellerList sellers={sellers} product={product} t={t} cpv={cpv} />
          : <p className="muted tender-note">{t.sellersNone} <b>{product}</b> {t.inCountry} {country}. {t.sellersWhy}</p>
      )}

      {!why && tab === "orders" && (
        orders.length > 0
          ? <OrderList orders={orders} product={product} t={t} cpv={cpv} />
          : <p className="muted tender-note">{t.ordersNone} <b>{product}</b> {t.inCountry} {country}.</p>
      )}
    </section>
  );
}
