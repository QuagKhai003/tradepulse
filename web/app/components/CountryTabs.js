"use client";
/**
 * CountryTabs.js — the three party views of one product IN one country: buyers, sellers, past orders.
 * @context  The globe answers "where is demand moving" — signals only. The moment you click a country
 *           you are asking about that market specifically, so the parties live HERE, on the country
 *           page, as tabs rather than three stacked lists (stacking made the page a scroll).
 *           Each tab is scoped to this country first: buyers whose organisation is here, sellers based
 *           here, orders this country took part in — with the product-wide rest available below.
 * @golden   Inform, never match — the lists themselves carry the rule; this only arranges them.
 * @limits   Presentation + tab state.
 * @affects  Rendered by country/[code]/page.js; wraps TenderList / SellerList / OrderList.
 */
import { useState } from "react";
import TenderList from "./TenderList.js";
import SellerList from "./SellerList.js";
import OrderList from "./OrderList.js";

export default function CountryTabs({ tHere, tElse, sellers, orders, product, country, cpv, lang, t }) {
  const [tab, setTab] = useState("buyers");
  const counts = { buyers: tHere.length + tElse.length, sellers: sellers.length, orders: orders.length };
  if (!counts.buyers && !counts.sellers && !counts.orders) return null;

  const tabs = [
    { v: "buyers", label: t.tabBuyers, n: counts.buyers },
    { v: "sellers", label: t.tabSellers, n: counts.sellers },
    { v: "orders", label: t.tabOrders, n: counts.orders },
  ];

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

      {tab === "buyers" && (
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
        </>
      )}

      {tab === "sellers" && (
        sellers.length > 0
          ? <SellerList sellers={sellers} product={product} t={t} cpv={cpv} />
          : <p className="muted tender-note">{t.sellersNone} <b>{product}</b> {t.inCountry} {country}. {t.sellersWhy}</p>
      )}

      {tab === "orders" && (
        orders.length > 0
          ? <OrderList orders={orders} product={product} t={t} cpv={cpv} />
          : <p className="muted tender-note">{t.ordersNone} <b>{product}</b> {t.inCountry} {country}.</p>
      )}
    </section>
  );
}
