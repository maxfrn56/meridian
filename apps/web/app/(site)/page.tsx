import type { Metadata } from "next";
import { Dashboard } from "@/components/landing/dashboard";
import { Faq } from "@/components/landing/faq";
import { FinalCta, SiteFooter } from "@/components/landing/final-cta";
import { Hero } from "@/components/landing/hero";
import { Pricing } from "@/components/landing/pricing";
import { SiteHeader } from "@/components/landing/site-header";
import { Steps } from "@/components/landing/steps";

export const metadata: Metadata = {
  title: "Meridian — Votre marque dans les réponses des IA",
  description:
    "Meridian mesure comment ChatGPT, Perplexity et Gemini parlent de votre entreprise, et vous aide à y être citée plus souvent et mieux placée que vos concurrents.",
};

export default function LandingPage() {
  return (
    <>
      <a className="lp-skip" href="#contenu">
        Aller au contenu
      </a>
      <SiteHeader />
      <main id="contenu">
        <Hero />
        <Steps />
        <Dashboard />
        <Pricing />
        <Faq />
        <FinalCta />
      </main>
      <SiteFooter />
    </>
  );
}
