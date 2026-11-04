"use client";

import { Fragment, useLayoutEffect, useRef } from "react";
import { motionEnabled } from "@/components/landing/motion";

/**
 * Titre de section révélé ligne par ligne : chaque mot est dans un masque, et tous les mots
 * d'une même ligne montent ensemble (--line, mesuré au rendu et à chaque redimensionnement).
 * Sans mouvement, c'est un titre ordinaire. Le déclenchement vient du Reveal parent.
 */
export function MaskedTitle({ id, className, text }: { id: string; className: string; text: string }) {
  const ref = useRef<HTMLHeadingElement>(null);

  useLayoutEffect(() => {
    const title = ref.current;
    if (!title || !motionEnabled()) return;
    const assign = () => {
      let line = -1;
      let top: number | null = null;
      title.querySelectorAll<HTMLElement>(".lp-mask").forEach((word) => {
        if (top === null || Math.abs(word.offsetTop - top) > 2) {
          line += 1;
          top = word.offsetTop;
        }
        word.style.setProperty("--line", String(line));
      });
    };
    assign();
    const observer = new ResizeObserver(assign);
    observer.observe(title);
    return () => observer.disconnect();
  }, []);

  return (
    <h2 ref={ref} id={id} className={className}>
      {text.split(" ").map((word, index) => (
        <Fragment key={index}>
          {index > 0 ? " " : null}
          <span className="lp-mask">
            <span className="lp-mask__inner">{word}</span>
          </span>
        </Fragment>
      ))}
    </h2>
  );
}
