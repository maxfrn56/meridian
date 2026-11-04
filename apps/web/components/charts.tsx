"use client";

import { useSyncExternalStore } from "react";
import { weekLabel } from "@/lib/format";
import type { Overview } from "@/lib/types";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/*
 * Graphiques de l'application, selon DESIGN.md :
 * - la marque du client est la seule donnée en orange ; les concurrents restent en gris ;
 * - traits de 2 px, axes et grilles discrets, textes en encre ou en gris, jamais dans la couleur de la série ;
 * - une légende dès qu'il y a deux séries ; apparition en 1,2 s, coupée si prefers-reduced-motion est actif.
 */

const INK = "#111318";
const MUTED = "#6b7280";
const GRID = "#eef0f3";
const BRAND = "#ff4f1a";
/* Gris des concurrents, du plus foncé (3,2:1) au plus clair : les plus clairs sont toujours étiquetés. */
const RIVALS = ["#8a909a", "#aeb3bb", "#c9cdd4", "#dde0e5"];

const axisTick = { fill: MUTED, fontSize: 12, fontFamily: "inherit" };

const tooltipStyle = {
  background: "#ffffff",
  border: "1px solid #e7e9ee",
  borderRadius: 12,
  boxShadow:
    "0 1px 2px rgb(17 19 24 / 0.04), 0 4px 12px rgb(17 19 24 / 0.05), 0 12px 32px -8px rgb(17 19 24 / 0.08)",
  color: INK,
  fontSize: 12,
  fontVariantNumeric: "tabular-nums",
};

const MOTION = { animationDuration: 1200, animationEasing: "ease-out" as const };

function subscribe(callback: () => void) {
  const query = window.matchMedia("(prefers-reduced-motion: reduce)");
  query.addEventListener("change", callback);
  return () => query.removeEventListener("change", callback);
}

function useReducedMotion() {
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => true,
  );
}

/* Trois mesures de la marque : le taux de citation porte l'orange, les deux autres restent neutres. */
const TREND_SERIES = [
  { key: "citation", label: "Taux de citation", stroke: BRAND, dash: undefined },
  { key: "voice", label: "Part de voix", stroke: INK, dash: undefined },
  { key: "geoScore", label: "Score GEO", stroke: RIVALS[0], dash: "4 3" },
] as const;

export function TrendLegend() {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {TREND_SERIES.map((serie) => (
        <li key={serie.key} className="inline-flex items-center gap-1.5">
          <svg width="14" height="2" aria-hidden="true">
            <line x1="0" y1="1" x2="14" y2="1" stroke={serie.stroke} strokeWidth="2" strokeDasharray={serie.dash} />
          </svg>
          {serie.label}
        </li>
      ))}
    </ul>
  );
}

export function TrendChart({ trend }: { trend: Overview["trend"] }) {
  const reduced = useReducedMotion();
  const data = trend.map((point) => ({
    ...point,
    label: weekLabel(point.week),
    citation: Math.round(point.citationRate * 100),
    voice: Math.round(point.shareOfVoice * 100),
  }));
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="label" tick={axisTick} axisLine={false} tickLine={false} />
          <YAxis tick={axisTick} axisLine={false} tickLine={false} unit="%" />
          <Tooltip
            contentStyle={tooltipStyle}
            cursor={{ stroke: "#c9cdd4", strokeWidth: 1 }}
            formatter={(value, name) => [
              `${value} %`,
              TREND_SERIES.find((serie) => serie.key === name)?.label ?? String(name),
            ]}
          />
          {TREND_SERIES.map((serie) => (
            <Line
              key={serie.key}
              type="monotone"
              dataKey={serie.key}
              name={serie.key}
              stroke={serie.stroke}
              strokeWidth={2}
              strokeDasharray={serie.dash}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, stroke: "#ffffff" }}
              connectNulls
              isAnimationActive={!reduced}
              {...MOTION}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SovChart({ slices }: { slices: Overview["shareOfVoice"] }) {
  const reduced = useReducedMotion();
  const data = slices.filter((slice) => slice.share > 0);
  if (!data.length) {
    return <p className="py-16 text-center text-sm text-muted-foreground">Pas encore de mentions.</p>;
  }
  const rivalIndex = new Map(
    data.filter((slice) => slice.kind !== "brand").map((slice, index) => [slice.name, index] as const),
  );
  const colorOf = (slice: (typeof data)[number]) =>
    slice.kind === "brand" ? BRAND : RIVALS[Math.min(rivalIndex.get(slice.name) ?? 0, RIVALS.length - 1)];
  return (
    <div>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="share"
              nameKey="name"
              innerRadius={64}
              outerRadius={88}
              stroke="#ffffff"
              strokeWidth={2}
              isAnimationActive={!reduced}
              {...MOTION}
            >
              {data.map((slice) => (
                <Cell key={slice.name} fill={colorOf(slice)} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value, _name, item) => {
                const share = typeof value === "number" ? value : 0;
                const payload =
                  item && typeof item === "object" && "payload" in item
                    ? (item.payload as { mentions?: number })
                    : undefined;
                return [`${Math.round(share * 100)} % · ${payload?.mentions ?? 0} mentions`, ""];
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 space-y-1.5 px-2 text-sm">
        {data.map((slice) => (
          <li key={slice.name} className="flex items-center justify-between gap-3">
            <span className={`flex items-center gap-2 ${slice.kind === "brand" ? "font-semibold" : ""}`}>
              <span className="size-2 rounded-full" style={{ background: colorOf(slice) }} />
              {slice.name}
            </span>
            <span className="tabular-nums text-muted-foreground">{Math.round(slice.share * 100)} %</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DomainChart({ domains }: { domains: Overview["topDomains"] }) {
  const reduced = useReducedMotion();
  if (!domains.length) {
    return <p className="py-10 text-sm text-muted-foreground">Aucune source externe pour l&apos;instant.</p>;
  }
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={domains} layout="vertical" margin={{ top: 0, right: 8, left: 16, bottom: 0 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="domain" width={140} tick={axisTick} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={tooltipStyle}
            cursor={{ fill: "#f6f7f9" }}
            formatter={(value) => [`${value} citations`, "Sources"]}
          />
          {/* Sources externes : aucune n'est la marque, toutes restent en gris. */}
          <Bar
            dataKey="citations"
            fill={RIVALS[0]}
            radius={[0, 4, 4, 0]}
            barSize={10}
            isAnimationActive={!reduced}
            {...MOTION}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
