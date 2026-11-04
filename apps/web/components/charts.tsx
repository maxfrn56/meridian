"use client";

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

const tooltipStyle = {
  background: "#121716",
  border: "1px solid rgba(232,239,235,0.12)",
  borderRadius: 8,
  fontSize: 12,
};

const RIVAL_COLORS = ["#e4b15a", "#8eb4ff", "#e07a6a", "#c084fc"];

export function TrendChart({ trend }: { trend: Overview["trend"] }) {
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
          <CartesianGrid stroke="rgba(232,239,235,0.06)" vertical={false} />
          <XAxis dataKey="label" tick={{ fill: "#93a29b", fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#93a29b", fontSize: 12 }} axisLine={false} tickLine={false} unit="%" />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value, name) => [`${value} %`, name === "citation" ? "Taux de citation" : name === "voice" ? "Part de voix" : "Score GEO"]}
          />
          <Line type="monotone" dataKey="citation" name="citation" stroke="#3dbea5" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="voice" name="voice" stroke="#8eb4ff" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="geoScore" name="score" stroke="#e4b15a" strokeWidth={2} dot={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SovChart({ slices }: { slices: Overview["shareOfVoice"] }) {
  const data = slices.filter((slice) => slice.share > 0);
  if (!data.length) {
    return <p className="py-16 text-center text-sm text-muted-foreground">Pas encore de mentions.</p>;
  }
  return (
    <div>
      <div className="h-52">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="share" nameKey="name" innerRadius={62} outerRadius={88} paddingAngle={2} stroke="none">
            {data.map((slice, index) => (
              <Cell key={slice.name} fill={slice.kind === "brand" ? "#3dbea5" : RIVAL_COLORS[index % RIVAL_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value, _name, item) => {
              const share = typeof value === "number" ? value : 0;
              const payload = item && typeof item === "object" && "payload" in item ? item.payload as { mentions?: number } : undefined;
              return [`${Math.round(share * 100)} % · ${payload?.mentions ?? 0} mentions`, ""];
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      </div>
      <ul className="mt-2 space-y-1 px-2 text-sm">
        {data.map((slice, index) => (
          <li key={slice.name} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2">
              <span
                className="size-2 rounded-full"
                style={{ background: slice.kind === "brand" ? "#3dbea5" : RIVAL_COLORS[index % RIVAL_COLORS.length] }}
              />
              {slice.name}
            </span>
            <span className="text-muted-foreground">{Math.round(slice.share * 100)} %</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DomainChart({ domains }: { domains: Overview["topDomains"] }) {
  if (!domains.length) {
    return <p className="py-10 text-sm text-muted-foreground">Aucune source externe pour l'instant.</p>;
  }
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={domains} layout="vertical" margin={{ top: 0, right: 8, left: 16, bottom: 0 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="domain" width={130} tick={{ fill: "#93a29b", fontSize: 12 }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle} formatter={(value) => [`${value} citations`, "Sources"]} />
          <Bar dataKey="citations" fill="#3dbea5" radius={[0, 6, 6, 0]} barSize={14} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
