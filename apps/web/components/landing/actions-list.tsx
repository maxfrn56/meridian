"use client";

import { useLayoutEffect, useRef, type CSSProperties } from "react";
import { ACTIONS } from "@/components/landing/data";
import { useMotionPlaying } from "@/components/landing/motion";

/*
 * « Corrigez dans le bon ordre » : les actions arrivent dans le désordre, puis se trient par priorité.
 * Le DOM est dans l'ordre final (c'est le rendu sans mouvement). SLOTS donne, pour chaque action,
 * sa place dans la liste désordonnée d'arrivée : Moyenne, Basse, Haute, Haute.
 */
const SLOTS = [3, 2, 0, 1];

const PRIORITY_CLASS: Record<string, string> = { Haute: "high", Moyenne: "mid", Basse: "low" };

export function ActionsList() {
  const playing = useMotionPlaying();
  const ref = useRef<HTMLOListElement>(null);

  // Décalage de chaque action entre sa place d'arrivée et sa place finale, mesuré (les titres font 1 ou 2 lignes).
  useLayoutEffect(() => {
    const list = ref.current;
    if (!list) return;
    const items = Array.from(list.children) as HTMLElement[];
    const tops = items.map((item) => item.offsetTop);
    items.forEach((item, index) => item.style.setProperty("--from", `${tops[SLOTS[index]] - tops[index]}px`));
  }, [playing]);

  return (
    <ol ref={ref}>
      {ACTIONS.map((action, index) => (
        <li key={action.title} style={{ "--slot": SLOTS[index] } as CSSProperties}>
          <span className={`lp-prio lp-prio--${PRIORITY_CLASS[action.priority]}`}>{action.priority}</span>
          <span>{action.title}</span>
          <span className="lp-num lp-muted">{action.impact}</span>
        </li>
      ))}
    </ol>
  );
}
