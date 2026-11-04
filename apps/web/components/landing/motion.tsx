"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ComponentPropsWithoutRef,
  type ElementType,
  type ReactNode,
} from "react";

/*
 * Mouvement de la landing.
 *
 * Le rendu serveur est toujours l'état final. Un script inline (voir app/(site)/layout.tsx) pose
 * la classe `lp-motion` sur <html> avant le premier affichage, seulement si JavaScript tourne et
 * que prefers-reduced-motion n'est pas actif. Les états de départ des animations n'existent que
 * sous cette classe : sans elle, tout s'affiche directement.
 *
 * Chaque bloc animé porte data-motion="wait", puis "play" quand il entre à l'écran, une seule fois.
 */

export const MOTION_CLASS = "lp-motion";

export function motionEnabled() {
  return typeof document !== "undefined" && document.documentElement.classList.contains(MOTION_CLASS);
}

const MotionContext = createContext(false);

export function MotionProvider({ playing, children }: { playing: boolean; children: ReactNode }) {
  return <MotionContext.Provider value={playing}>{children}</MotionContext.Provider>;
}

export function useMotionPlaying() {
  return useContext(MotionContext);
}

/** Appelle onEnter une fois, quand l'élément est assez visible. Ne fait rien si le mouvement est coupé. */
export function useEnterOnce<T extends Element>(onEnter: () => void, threshold = 0.35) {
  const ref = useRef<T>(null);
  const callback = useRef(onEnter);

  useEffect(() => {
    callback.current = onEnter;
  });

  useEffect(() => {
    const element = ref.current;
    if (!element || !motionEnabled()) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return;
        observer.disconnect();
        callback.current();
      },
      { threshold, rootMargin: "0px 0px -8% 0px" },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [threshold]);

  return ref;
}

type RevealProps<T extends ElementType> = {
  as?: T;
  threshold?: number;
} & Omit<ComponentPropsWithoutRef<T>, "as">;

/** Bloc qui joue sa séquence une fois, à son entrée à l'écran. Ne change rien à la mise en page. */
export function Reveal<T extends ElementType = "div">({ as, threshold, children, ...rest }: RevealProps<T>) {
  const Tag: ElementType = as ?? "div";
  const [playing, setPlaying] = useState(false);
  const ref = useEnterOnce<HTMLElement>(() => setPlaying(true), threshold);
  return (
    <MotionContext.Provider value={playing}>
      <Tag ref={ref} data-motion={playing ? "play" : "wait"} {...rest}>
        {children}
      </Tag>
    </MotionContext.Provider>
  );
}

/* La courbe commune (--ease-out), cubic-bezier(0.33, 1, 0.68, 1), évaluée pour les compteurs. */
const P1X = 0.33;
const P1Y = 1;
const P2X = 0.68;
const P2Y = 1;

function bezier(t: number, a: number, b: number) {
  const u = 1 - t;
  return 3 * u * u * t * a + 3 * u * t * t * b + t * t * t;
}

export function easeOut(x: number) {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  let t = x;
  for (let i = 0; i < 8; i += 1) {
    const current = bezier(t, P1X, P2X) - x;
    const u = 1 - t;
    const slope = 3 * u * u * P1X + 6 * u * t * (P2X - P1X) + 3 * t * t * (1 - P2X);
    if (Math.abs(current) < 1e-5 || slope === 0) break;
    t -= current / slope;
  }
  return bezier(t, P1Y, P2Y);
}

function format(value: number, decimals: number) {
  return value.toFixed(decimals).replace(".", ",");
}

/**
 * Nombre qui se calcule jusqu'à sa valeur quand son bloc joue.
 * Le rendu serveur affiche directement la valeur finale.
 */
export function CountUp({
  value,
  from = 0,
  decimals = 0,
  suffix = "",
  duration = 1200,
  delay = 0,
}: {
  value: number;
  from?: number;
  decimals?: number;
  suffix?: string;
  duration?: number;
  delay?: number;
}) {
  const playing = useMotionPlaying();
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const element = ref.current;
    if (!playing || !element || !motionEnabled()) return;
    let frame = 0;
    const start = performance.now() + delay;
    element.textContent = format(from, decimals) + suffix;
    const tick = (now: number) => {
      const progress = Math.min(1, Math.max(0, (now - start) / duration));
      element.textContent = format(from + (value - from) * easeOut(progress), decimals) + suffix;
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, value, from, decimals, suffix, duration, delay]);

  return (
    <span ref={ref} className="lp-count">
      {format(value, decimals)}
      {suffix}
    </span>
  );
}
