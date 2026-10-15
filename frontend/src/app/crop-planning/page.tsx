"use client";

import { useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  CalendarDays,
  Check,
  EyeOff,
  Leaf,
  MapPin,
  NotebookPen,
  ShieldCheck,
  Sparkles,
  Sprout,
  TrendingDown,
  Zap,
  FlaskConical,
  Globe,
} from "lucide-react";
import { Button } from "./components/ui/button";
import { Card as UiCard } from "./components/ui/card";

const features = [
  {
    icon: BarChart3,
    number: "01",
    tag: "CONCENTRATION RISK",
    title: "Understand the cultivation picture",
    text: "Explore descriptive concentration analysis for your saved plan using K-Means and DBSCAN density clustering, with complete privacy preservation.",
    link: "/crop-planning/risk-analysis",
    label: "Explore analysis",
    bg: "from-emerald-50 to-green-50",
  },
  {
    icon: Leaf,
    number: "02",
    tag: "ALTERNATIVE CROPS",
    title: "Consider crops with context",
    text: "Review conditional crop comparisons when independent agro-ecological suitability approvals and comparable district coverage support them.",
    link: "/crop-planning/suggested-crops",
    label: "Explore crop comparisons",
    bg: "from-lime-50 to-emerald-50",
  },
  {
    icon: CalendarDays,
    number: "03",
    tag: "PERSONALIZED SCHEDULES",
    title: "Bring your season together",
    text: "Organize cultivation records and build an actionable activity timeline from guidelines explicitly verified and approved for your locality.",
    link: "/crop-planning/cultivation-plan",
    label: "Explore cultivation planning",
    bg: "from-teal-50 to-green-50",
  },
];

const stats = [
  {
    icon: MapPin,
    value: "2 Pilot Districts",
    label: "Matara & Hambantota coverage",
  },
  {
    icon: Sprout,
    value: "6 Commercial Crops",
    label: "Corn, Mung Beans, Bandakka & more",
  },
  {
    icon: EyeOff,
    value: "100% Privacy",
    label: "Collective farmer data withheld",
  },
  {
    icon: ShieldCheck,
    value: "Evidence-Gated",
    label: "No fabricated risk classifications",
  },
];

const benefits = [
  {
    title: "Your records, all together",
    text: "Manage your individual cultivation plans, acreage, planting dates, and saved personalized schedule revisions in one secure place.",
  },
  {
    title: "Clear, honest evidence",
    text: "See when analysis ran, what evidence is missing, and which activities carry official agricultural approvals. No ungrounded claims.",
  },
  {
    title: "Privacy built into the journey",
    text: "Explore your plan without revealing your identity or accessing other farmers' protected counts, collective acreage, or clustering details.",
  },
];

export default function HomePage() {
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.location.replace("/crop-planning/dashboard");
    }
  }, []);

  return (
    <>
      {/* ─── HERO ──────────────────────────────────────── */}
      <section className="cp-landing-hero cp-container">
        <div className="cp-landing-copy">
          <div className="cp-pill">
            <Link href="/" style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "inherit", textDecoration: "none" }}>
              <Sparkles size={13} aria-hidden="true" />
              <span>AIMS RESEARCH • OUR SERVICES • VIEW MAIN PORTAL →</span>
            </Link>
          </div>

          <h1>
            Plan Smarter.<br />
            <em>Cultivate with</em><br />
            Confidence.
          </h1>

          <p>
            An intelligent decision-support system for modern farmers. Understand
            cultivation concentration patterns, explore evidence-backed alternative crops,
            and build personalized activity schedules for your next season.
          </p>

          <div className="cp-actions">
            <Button asChild size="lg" className="cp-hero-btn-primary">
              <Link href="/crop-planning/register">
                Get started
                <ArrowRight size={17} aria-hidden="true" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="cp-hero-btn-secondary">
              <Link href="/crop-planning/login">Farmer login</Link>
            </Button>
          </div>

          <div className="cp-hero-trust">
            <ShieldCheck size={16} className="text-emerald-600" aria-hidden="true" />
            <span>Your records stay private. No collective data disclosed.</span>
          </div>
        </div>

        <div className="cp-landing-visual">
          <Image
            src="/crop-planning/agfarm_hero.jpg"
            alt="Aerial view of lush Sri Lankan agricultural terraces and crop fields at golden hour"
            fill
            priority
            sizes="(max-width: 900px) 100vw, 50vw"
            className="cp-field-image"
          />
          <div className="cp-image-overlay" />
          <div className="cp-image-label">
            <span className="cp-image-icon">
              <Sprout size={22} aria-hidden="true" />
            </span>
            <div>
              <span>RESEARCH-BACKED PLATFORM</span>
              <strong>Precision crop intelligence for Sri Lankan agriculture.</strong>
            </div>
          </div>
          <div className="cp-visual-caption">
            <Leaf size={14} aria-hidden="true" />
            From planting intentions to evidence-based cultivation decisions
          </div>
        </div>
      </section>

      {/* ─── STATS BANNER ──────────────────────────────── */}
      <section className="cp-stats-strip" aria-label="Platform highlights">
        <div className="cp-container cp-stats-grid">
          {stats.map((stat) => (
            <div key={stat.value} className="cp-stat-item">
              <span className="cp-stat-icon">
                <stat.icon size={19} aria-hidden="true" />
              </span>
              <div>
                <strong>{stat.value}</strong>
                <small>{stat.label}</small>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── CAPABILITY TICKER ─────────────────────────── */}
      <div className="cp-capability-strip">
        <div className="cp-container">
          <span>INTEGRATED DECISION WORKSPACE</span>
          <p>
            <NotebookPen size={16} aria-hidden="true" />
            Cultivation records
          </p>
          <p>
            <BarChart3 size={16} aria-hidden="true" />
            Descriptive analysis
          </p>
          <p>
            <Leaf size={16} aria-hidden="true" />
            Eligible crop alternatives
          </p>
          <p>
            <CalendarDays size={16} aria-hidden="true" />
            Approved activity timelines
          </p>
        </div>
      </div>

      {/* ─── MAIN FEATURES ─────────────────────────────── */}
      <section id="features" className="cp-container cp-landing-section">
        <div className="cp-section-heading">
          <div>
            <span className="cp-eyebrow">RESEARCH CAPABILITIES</span>
            <h2>
              Every step of your next season.<br />
              <em>Thoughtfully connected.</em>
            </h2>
          </div>
          <p>
            Avoid over-concentration risks with data-driven clustering insights and
            agro-ecological suitability verification.
          </p>
        </div>

        <div className="cp-feature-grid">
          {features.map((feature) => (
            <UiCard key={feature.number} className="cp-feature-card">
              <div className="cp-feature-top">
                <span className="cp-icon-tile">
                  <feature.icon size={23} strokeWidth={1.8} aria-hidden="true" />
                </span>
                <span className="cp-feature-tag">{feature.tag}</span>
                <span className="cp-feature-num">{feature.number}</span>
              </div>
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
              <Link href={feature.link} className="cp-feature-link">
                <span>{feature.label}</span>
                <ArrowUpRight size={16} aria-hidden="true" />
              </Link>
            </UiCard>
          ))}
        </div>
      </section>

      {/* ─── HOW IT WORKS ──────────────────────────────── */}
      <section id="how-it-works" className="cp-how-section">
        <div className="cp-container">
          <div className="cp-centered-heading">
            <span className="cp-eyebrow">SYSTEM WORKFLOW</span>
            <h2>
              A structured path to a<br />
              <em>better-planned season.</em>
            </h2>
          </div>

          <ol className="cp-how-grid" style={{ listStyle: "none", padding: 0 }}>
            {[
              {
                title: "Tell us what you plan to grow",
                text: "Register your farmer account and log your intended crop, district, locality, acreage, planting date, and declared season.",
                icon: NotebookPen,
              },
              {
                title: "See what the evidence says",
                text: "Trigger descriptive concentration analysis on your saved plan and review conditional alternative comparisons when evidence permits.",
                icon: BarChart3,
              },
              {
                title: "Build your cultivation schedule",
                text: "Generate verified activity timelines based only on approved agricultural guidelines, save revisions, and track progress.",
                icon: CalendarDays,
              },
            ].map((step, index) => (
              <li key={step.title} className="cp-how-card">
                <div className="cp-how-header">
                  <span className="cp-step-number">0{index + 1}</span>
                  <span className="cp-step-icon">
                    <step.icon size={18} aria-hidden="true" />
                  </span>
                </div>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ─── BENEFITS ──────────────────────────────────── */}
      <section className="cp-container cp-landing-section cp-benefits">
        <div>
          <span className="cp-eyebrow">BUILT AROUND THE FARMER</span>
          <h2>
            Your farm.<br />
            Your context.<br />
            <em>Your next move.</em>
          </h2>
          <p>
            AgFarm provides clear, honest insights without synthetic predictions. Everything is
            grounded in verifiable evidence and tailored to your individual plot.
          </p>
          <Button asChild size="lg">
            <Link href="/crop-planning/register">
              Create your farmer account
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </Button>
        </div>

        <div className="cp-benefit-list">
          {benefits.map((item) => (
            <div key={item.title} className="cp-benefit-item">
              <span className="cp-benefit-icon">
                <Check size={16} aria-hidden="true" />
              </span>
              <div>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── RESEARCH INTEGRITY ────────────────────────── */}
      <section id="research" className="cp-container cp-research-band">
        <span className="cp-icon-tile">
          <ShieldCheck size={26} aria-hidden="true" />
        </span>
        <div>
          <h3>Research with clear boundaries.</h3>
          <p>
            The research model is a retrospectively evaluated concentration proxy. It does not
            establish live market-loss risk. Current classifications and guidance depend on
            independent evidence and approval. This is a university research demonstration system.
          </p>
        </div>
        <span className="cp-research-label">COMPONENT 02</span>
      </section>

      {/* ─── FINAL CTA ─────────────────────────────────── */}
      <section className="cp-container cp-final-cta">
        <div className="cp-final-cta-card">
          <span className="cp-eyebrow">GIVE YOUR NEXT SEASON A CLEARER START</span>
          <h2>
            Good planning starts<br />
            with <em>your first record.</em>
          </h2>
          <p>Create a free farmer account and explore your cultivation context today.</p>
          <div className="cp-actions justify-center">
            <Button asChild size="lg" className="cp-btn-white">
              <Link href="/crop-planning/register">
                Get started free
                <ArrowRight size={17} aria-hidden="true" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="cp-btn-translucent">
              <Link href="/crop-planning/login">Log in to your workspace</Link>
            </Button>
          </div>
          <p className="cp-cta-footnote">
            Already have an account?{" "}
            <Link href="/crop-planning/login">Log in to your workspace</Link>
          </p>
        </div>
      </section>
    </>
  );
}
