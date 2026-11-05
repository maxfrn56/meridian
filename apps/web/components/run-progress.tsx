"use client";

import { ApiError, api } from "@/lib/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

type RunProgress = {
  running: boolean;
  done: number;
  total: number;
  percent: number;
  label: string;
};

const HELD_MS = 1400;

export async function runTracking(
  body: Record<string, unknown>,
  onTick?: (progress: RunProgress) => void,
) {
  const started = await api<RunProgress>("/tracking/run", { method: "POST", body: JSON.stringify(body) });
  onTick?.(started);
  let current = started;
  while (current.running) {
    await new Promise((resolve) => setTimeout(resolve, 700));
    current = await api<RunProgress>("/tracking/progress");
    onTick?.(current);
  }
  if (current.label && current.label !== "Suivi terminé.") {
    throw new ApiError(current.label, 400);
  }
  return current;
}

export function useTrackingLaunch(request: () => Promise<unknown>, refresh: () => Promise<void>) {
  const [done, setDone] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  const run = useMutation({
    mutationFn: request,
    onMutate: () => {
      if (timer.current) clearTimeout(timer.current);
      setDone(false);
    },
    onSuccess: async () => {
      setDone(true);
      await refresh();
      timer.current = setTimeout(() => setDone(false), HELD_MS);
    },
    onError: () => setDone(false),
  });

  return { run, active: run.isPending || done, complete: done && !run.isPending };
}

export function RunProgressBar({ active, complete = false }: { active: boolean; complete?: boolean }) {
  const [live, setLive] = useState<RunProgress | null>(null);

  useEffect(() => {
    if (!active || complete) return;
    let stop = false;

    async function tick() {
      try {
        const next = await api<RunProgress>("/tracking/progress");
        if (!stop) setLive(next);
      } catch {
        /* La barre reste sur la dernière valeur connue. */
      }
    }

    void tick();
    const timer = setInterval(() => void tick(), 700);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, [active, complete]);

  if (!active) return null;

  const percent = complete ? 100 : live?.running ? live.percent : 0;
  const label = complete ? "Suivi terminé." : live?.running && live.label ? live.label : "Envoi des questions…";

  return (
    <div className="mb-4" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-sm font-semibold">{label}</p>
        <p className="tabular-nums text-sm font-semibold">{percent} %</p>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full bg-foreground transition-[width] duration-300" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

export function useRefreshAfterRun() {
  const queryClient = useQueryClient();
  return async () => {
    await queryClient.invalidateQueries({ queryKey: ["overview"] });
    await queryClient.invalidateQueries({ queryKey: ["tracking"] });
    await queryClient.invalidateQueries({ queryKey: ["billing"] });
  };
}
