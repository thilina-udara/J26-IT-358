"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  CloudRain,
  ExternalLink,
  Info,
  Leaf,
  MapPin,
  Play,
  QrCode,
  Recycle,
  ShieldCheck,
  Sparkles,
  Sprout,
  Star,
  TrendingUp,
  Users,
  X,
  Phone,
  Mail,
  ChevronRight,
  Activity,
  Layers,
  Check,
} from "lucide-react";

export default function HomePage() {
  const [activeModalComponent, setActiveModalComponent] = useState<number | null>(null);

  const componentsData = [
    {
      id: 1,
      title: "Market Demand, Price Trend & Profit Risk Prediction",
      shortTitle: "Market Intelligence & Profit Risk",
      category: "Component 01",
      badgeText: "Market Intelligence",
      image: "/images/component1_market.jpg",
      tagColor: "#1d4ed8",
      tagBg: "#dbeafe",
      description:
        "Predicts harvest-period market demand, price collapse warnings, and farm-level net profitability before planting using advanced machine learning time-series models.",
      gapAddressed:
        "Existing systems mainly show current or historical prices, but they fail to inform farmers whether a selected crop will remain profitable during the actual harvest window weeks ahead.",
      inputs: [
        "Historical wholesale crop prices (Dambulla, Pettah, Meegoda wholesale hubs)",
        "Seasonal consumption patterns & harvest volume trends",
        "Expected regional supply and historical yield metrics",
        "Cultivation, transport, labor, and market commission costs",
      ],
      process:
        "Integrates ARIMA, LSTM, Prophet, Random Forest, and XGBoost to forecast future crop prices and demand. Calculates Revenue = (Predicted Price × Expected Yield) and Profit = Revenue − Total Cost, classifying crops into Low, Medium, or High Profit Risk.",
      outputs: [
        "Future harvest-period price & demand forecasts",
        "Expected revenue and net margin predictions",
        "Price-drop & oversupply early warning alerts",
        "Profit-risk level rating and pre-planting crop recommendations",
      ],
      href: "/crop-planning/suggested-crops",
      actionText: "Explore Market Intelligence",
      isLive: false,
    },
    {
      id: 2,
      title:
        "AI-Based Cultivation Concentration Risk Analysis & Personalized Crop Planning",
      shortTitle: "Cultivation Concentration & Crop Planning",
      category: "Component 02 • Core Module (Active)",
      badgeText: "Cultivation Planning (Live)",
      image: "/images/component2_planning.jpg",
      tagColor: "#15803d",
      tagBg: "#dcfce7",
      description:
        "Detects pre-planting crop concentration using K-Means and DBSCAN clustering, recommends lower-risk alternative crops, and generates personalized agronomic schedules.",
      gapAddressed:
        "Farmers cultivate crops without visibility into other farmers' intentions in the same region, leading to severe harvest congestion, oversupply, and catastrophic financial losses.",
      inputs: [
        "Farmer planned crop type & acreage (land size)",
        "Planned planting date and expected harvest period",
        "District & agro-ecological zone",
        "Collective farmer cultivation records & DoA guidelines",
      ],
      process:
        "Farmers submit plans prior to planting. K-Means groups collective plans by crop, region, harvest period, and acreage. DBSCAN detects high-density concentration hotspots and anomalous records. Evaluates concentration risk, recommends lower-risk alternative crops, and generates personalized DoA cultivation schedules.",
      outputs: [
        "Pre-planting cultivation concentration risk score (Low / Medium / High / Critical)",
        "Agro-ecologically verified alternative crop recommendations",
        "Head-to-head crop comparison matrix",
        "Personalized cultivation calendar (land prep, seeding, fertilizer, harvest)",
      ],
      href: "/crop-planning",
      actionText: "Launch Crop Planning Module",
      isLive: true,
    },
    {
      id: 3,
      title:
        "Barcode-Based Produce Tracking, Waste Management & Organic Fertilizer Management",
      shortTitle: "Produce Traceability & Circular Waste Recovery",
      category: "Component 03 • Core Bioeconomy & Tracking (Live)",
      badgeText: "Traceability & Waste (Live)",
      image: "/images/component3_waste.jpg",
      tagColor: "#15803d",
      tagBg: "#dcfce7",
      description:
        "Farm-to-market crate barcode traceability (BC-000001+), real-time XGBoost spoilage risk scoring, and circular economy recovery into organic bio-fertilizer and biogas.",
      gapAddressed:
        "Produce collection and transport are fragmented and manual. Rejected, damaged, or unsold produce is dumped in landfills rather than recovered as low-cost organic fertilizer.",
      inputs: [
        "Farmer ID, crop variety, harvest date, and crate batch barcode (BC-000001+)",
        "Collection centre receipts and transit monitoring logs",
        "Rejected, damaged, or unsold produce records",
        "Regional organic fertilizer demand from farmers and home gardeners",
      ],
      process:
        "Produce lots registered via crate barcode stickers. The system tracks collection, transport, and stock movement. Evaluates spoilage risk with XGBoost, partitions fresh vs cull waste streams, and optimizes composting recipe allocation.",
      outputs: [
        "End-to-end produce traceability records and transit status",
        "Quantitative in-transit spoilage risk prediction (ŷ loss %)",
        "Produce waste risk classification score (Low / Medium / High)",
        "Organic compost yield estimates and fertilizer distribution plans",
      ],
      href: "/waste-management",
      actionText: "Launch Transport Tracking & Waste Module",
      isLive: true,
    },
    {
      id: 4,
      title:
        "AI-Powered National Early Warning & Policy Decision Support Engine",
      shortTitle: "National Climate Early Warning & Policy Engine",
      category: "Component 04",
      badgeText: "Climate & GIS Engine",
      image: "/images/component4_climate.jpg",
      tagColor: "#7e22ce",
      tagBg: "#f3e8ff",
      description:
        "National and district-level multi-hazard climate forecasting (drought, flood, ENSO, reservoir levels) with automated pre-planting alert routing to farmers and policymakers.",
      gapAddressed:
        "Weather systems report rainfall as isolated events without calculating direct agricultural crop failure risk, reservoir depletion, or national food supply balance deficits.",
      inputs: [
        "Historical & forecasted climate data (rainfall, temperature, ENSO indices)",
        "Reservoir water storage levels & irrigation water availability",
        "Regional crop vulnerability and historical flood/drought damage",
        "National food balance metrics & economic indicators",
      ],
      process:
        "Analyses multi-hazard climate data using LSTM, LightGBM, and XGBoost. Evaluates hazard severity, cultivated land exposure, and crop vulnerability to compute district-level risk scores. Automatically routes alerts to farmer planning tools before planting.",
      outputs: [
        "Multi-hazard drought, flood, and ENSO warning alerts",
        "District-level agricultural risk scores & interactive GIS maps",
        "Irrigation water limitation forecasts",
        "National food deficit projections and policy decision support briefs",
      ],
      href: "/crop-planning/risk-analysis",
      actionText: "Explore National Early Warning",
      isLive: false,
    },
  ];

  return (
    <div>
      {/* --------------------------------------------------------------------------
          HEADER / NAVBAR (Kishan Sathi Exact Format)
          -------------------------------------------------------------------------- */}
      <header className="portal-navbar">
        <div className="portal-navbar-inner">
          {/* Brand Logo */}
          <Link href="/" className="portal-logo-group">
            <div className="portal-logo-icon">
              <Sprout size={26} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span className="portal-logo-text">AgroDecision</span>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 800,
                    padding: "2px 6px",
                    borderRadius: "4px",
                    backgroundColor: "#dcfce7",
                    color: "#166534",
                  }}
                >
                  AI
                </span>
              </div>
              <div className="portal-logo-tag">
                Your Farming Partner • AIMS Research
              </div>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="portal-nav-links">
            <a href="#hero" style={{ color: "#15803d" }}>Home</a>
            <Link href="/waste-management" style={{ fontWeight: 700, color: "#15803d" }}>
              Waste & Transport Tracking
            </Link>
            <a href="#services">Our Services</a>
            <a href="#about">About Us</a>
            <a href="#features">Key Features</a>
            <a href="#sdgs">SDGs</a>
          </nav>

          {/* Action Buttons */}
          <div className="portal-nav-actions">
            <Link href="/crop-planning/login" className="portal-btn-login">
              Login
            </Link>
            <Link href="/crop-planning/register" className="portal-btn-signup">
              Sign Up
              <ArrowRight size={15} />
            </Link>
          </div>
        </div>
      </header>

      {/* --------------------------------------------------------------------------
          HERO SECTION (Matching Reference Image)
          -------------------------------------------------------------------------- */}
      <section id="hero" className="portal-hero-section">
        <div className="portal-container">
          <div className="portal-hero-grid">

            {/* Left Column */}
            <div>
              <div className="portal-hero-badge">
                <Leaf size={14} />
                Digital Support For Resilient Farming
              </div>

              <h1 className="portal-hero-title">
                <em>Data-Driven Farmer Decision System</em>
                Your Smart Farming Partner
              </h1>

              <p className="portal-hero-desc">
                Get collaborative pre-planting intelligence, real-time climate risk alerts, harvest-period market price forecasts, produce traceability, and circular organic waste recovery — all in one unified Sri Lankan platform.
                Empowering farmers with data-driven decision tools for a prosperous future.
              </p>

              {/* Action Buttons */}
              <div className="portal-hero-actions">
                <Link href="/crop-planning" className="portal-btn-primary">
                  Get Started
                  <ArrowRight size={18} />
                </Link>

                <a href="#services" className="portal-btn-outline">
                  <Play size={16} style={{ color: "#15803d", fill: "#15803d" }} />
                  Explore Our Services
                </a>
              </div>

              {/* Verified Badges */}
              <div className="portal-hero-pills">
                <span>
                  <CheckCircle2 size={16} style={{ color: "#15803d" }} />
                  AIMS Research Group
                </span>
                <span>
                  <CheckCircle2 size={16} style={{ color: "#15803d" }} />
                  Faculty of Computing (IT)
                </span>
                <span>
                  <CheckCircle2 size={16} style={{ color: "#15803d" }} />
                  Pre-Planting Oversupply Risk Mitigation
                </span>
              </div>
            </div>

            {/* Right Column: Hero Farmer Image */}
            <div className="portal-hero-img-wrap">
              <div className="portal-hero-img-card">
                <img
                  src="/images/hero_farmer.jpg"
                  alt="Sri Lankan farmer using AgroDecision smartphone app in vegetable field"
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------------
          STATS BANNER (4 Cards Matching Reference Screenshot)
          -------------------------------------------------------------------------- */}
      <section className="portal-stats-bar">
        <div className="portal-container">
          <div className="portal-stats-grid">

            <div className="portal-stat-item">
              <div className="portal-stat-icon-wrap" style={{ background: "#ecfdf5", color: "#059669" }}>
                <Users size={26} />
              </div>
              <div>
                <div className="portal-stat-val">50K+</div>
                <div className="portal-stat-lbl">Active Farmers & Plans</div>
              </div>
            </div>

            <div className="portal-stat-item">
              <div className="portal-stat-icon-wrap" style={{ background: "#f7fee7", color: "#65a30d" }}>
                <Sprout size={26} />
              </div>
              <div>
                <div className="portal-stat-val">100+</div>
                <div className="portal-stat-lbl">Crop Varieties & Guides</div>
              </div>
            </div>

            <div className="portal-stat-item">
              <div className="portal-stat-icon-wrap" style={{ background: "#f0f9ff", color: "#0284c7" }}>
                <CloudRain size={26} />
              </div>
              <div>
                <div className="portal-stat-val">Real-time</div>
                <div className="portal-stat-lbl">Climate & Water Alerts</div>
              </div>
            </div>

            <div className="portal-stat-item">
              <div className="portal-stat-icon-wrap" style={{ background: "#fffbeb", color: "#d97706" }}>
                <TrendingUp size={26} />
              </div>
              <div>
                <div className="portal-stat-val">Live AI</div>
                <div className="portal-stat-lbl">Market Price Forecasts</div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------------
          ABOUT US SECTION (Matching Screenshot Layout)
          -------------------------------------------------------------------------- */}
      <section id="about" className="portal-about-section">
        <div className="portal-container">
          <div className="portal-about-grid">

            {/* Left: Image with badge */}
            <div className="portal-about-img-wrap">
              <img
                src="/images/about_farmer.jpg"
                alt="Extension officer and farmer inspecting tablet in Sri Lankan farm"
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
              <div className="portal-about-img-tag">
                <Leaf size={14} />
                Technology for Better Farming
              </div>
            </div>

            {/* Middle: Content */}
            <div>
              <div className="portal-section-label">
                <span style={{ width: "20px", height: "2px", background: "#15803d", display: "inline-block" }} />
                About Us & Research
              </div>

              <h2 className="portal-section-title">
                We&apos;re here to support our farmers
              </h2>

              <p className="portal-about-text">
                Sri Lankan farmers, especially small and medium-scale vegetable and fruit growers, often make cultivation decisions using current prices, previous-season experience, or informal advice.
              </p>

              <p className="portal-about-text">
                With limited visibility into neighboring farmers’ pre-planting intentions, severe market oversupply, harvest gluts, and drastic price drops occur. Developed by the <strong>AIMS Research Group</strong> (Faculty of Computing, IT Specialization), AgroDecision AI integrates collaborative cultivation planning, profit-risk forecasting, produce tracking, and circular organic fertilizer recovery in simple, accessible language.
              </p>

              <a href="#services" className="portal-btn-primary" style={{ padding: "10px 22px", fontSize: "13px" }}>
                Learn More
                <ArrowRight size={15} />
              </a>
            </div>

            {/* Right: Stacked Cards */}
            <div>
              <div className="portal-stacked-card">
                <div style={{ width: "42px", height: "42px", borderRadius: "12px", background: "#dcfce7", color: "#166534", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Leaf size={22} />
                </div>
                <div>
                  <div style={{ fontSize: "17px", fontWeight: 800, color: "#0f172a" }}>100+</div>
                  <div style={{ fontSize: "12px", color: "#64748b" }}>Expert Farming Tips & Guides</div>
                </div>
              </div>

              <div className="portal-stacked-card">
                <div style={{ width: "42px", height: "42px", borderRadius: "12px", background: "#dbeafe", color: "#1d4ed8", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Users size={22} />
                </div>
                <div>
                  <div style={{ fontSize: "17px", fontWeight: 800, color: "#0f172a" }}>50K+</div>
                  <div style={{ fontSize: "12px", color: "#64748b" }}>Active Farmers & Plans</div>
                </div>
              </div>

              <div className="portal-stacked-card">
                <div style={{ width: "42px", height: "42px", borderRadius: "12px", background: "#fef3c7", color: "#b45309", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Star size={22} style={{ fill: "#b45309" }} />
                </div>
                <div>
                  <div style={{ fontSize: "17px", fontWeight: 800, color: "#0f172a" }}>4.8★</div>
                  <div style={{ fontSize: "12px", color: "#64748b" }}>Model Validation Rating</div>
                </div>
              </div>

              <div className="portal-stacked-card">
                <div style={{ width: "42px", height: "42px", borderRadius: "12px", background: "#f3e8ff", color: "#7e22ce", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Activity size={22} />
                </div>
                <div>
                  <div style={{ fontSize: "17px", fontWeight: 800, color: "#0f172a" }}>24/7</div>
                  <div style={{ fontSize: "12px", color: "#64748b" }}>National Early Warning Alerts</div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------------
          KEY FEATURES ("Everything You Need for Smart Farming")
          -------------------------------------------------------------------------- */}
      <section id="features" className="portal-features-section">
        <div className="portal-container">
          <div className="portal-features-header">
            <div style={{ display: "inline-block", fontSize: "11px", fontWeight: 800, color: "#15803d", textTransform: "uppercase", letterSpacing: "1px", background: "#dcfce7", padding: "4px 12px", borderRadius: "9999px", marginBottom: "12px" }}>
              KEY FEATURES
            </div>
            <h2 className="portal-section-title" style={{ textAlign: "center" }}>
              Everything You Need for Smart Farming
            </h2>
            <p style={{ fontSize: "15px", color: "#64748b" }}>
              From pre-planting risk analysis to market prices, we bring all essential information at your fingertips.
            </p>
          </div>

          <div className="portal-features-grid">

            {/* Card 1 */}
            <div className="portal-feature-card">
              <div>
                <div className="portal-icon-circle" style={{ background: "#22c55e" }}>
                  <CloudRain size={24} />
                </div>
                <h3 className="portal-feature-title">Weather & Climate Updates</h3>
                <p className="portal-feature-text">
                  Get real-time and 7-day weather forecasts, district-level rainfall predictions, and drought warnings tailored for your location.
                </p>
              </div>
              <div className="portal-feature-tag" style={{ color: "#15803d" }}>
                Multi-Hazard GIS Engine <ArrowRight size={14} />
              </div>
            </div>

            {/* Card 2 */}
            <div className="portal-feature-card">
              <div>
                <div className="portal-icon-circle" style={{ background: "#f59e0b" }}>
                  <Sprout size={24} />
                </div>
                <h3 className="portal-feature-title">Crop Guidance & Planning</h3>
                <p className="portal-feature-text">
                  Learn about the best crops, seeds, fertilizer schedules, and personalized farming methods approved by standard agricultural guidelines.
                </p>
              </div>
              <div className="portal-feature-tag" style={{ color: "#b45309" }}>
                DoA Standard Schedules <ArrowRight size={14} />
              </div>
            </div>

            {/* Card 3 */}
            <div className="portal-feature-card">
              <div>
                <div className="portal-icon-circle" style={{ background: "#3b82f6" }}>
                  <TrendingUp size={24} />
                </div>
                <h3 className="portal-feature-title">Market Prices & Profit</h3>
                <p className="portal-feature-text">
                  Check live market prices, predict harvest-period rates, and calculate expected net revenue and profit-risk before investing.
                </p>
              </div>
              <div className="portal-feature-tag" style={{ color: "#1d4ed8" }}>
                LSTM & ARIMA Price Models <ArrowRight size={14} />
              </div>
            </div>

            {/* Card 4 */}
            <div className="portal-feature-card">
              <div>
                <div className="portal-icon-circle" style={{ background: "#8b5cf6" }}>
                  <Users size={24} />
                </div>
                <h3 className="portal-feature-title">Expert Advice</h3>
                <p className="portal-feature-text">
                  Ask questions, review regional cultivation insights, and receive guidance from agricultural extension officers and smart AI agents.
                </p>
              </div>
              <div className="portal-feature-tag" style={{ color: "#6d28d9" }}>
                Extension Officer Support <ArrowRight size={14} />
              </div>
            </div>

            {/* Card 5 */}
            <div className="portal-feature-card">
              <div>
                <div className="portal-icon-circle" style={{ background: "#ef4444" }}>
                  <ShieldCheck size={24} />
                </div>
                <h3 className="portal-feature-title">Risk Notifications</h3>
                <p className="portal-feature-text">
                  Stay updated with early warnings for regional oversupply, sudden price crashes, reservoir depletion, and climate hazards.
                </p>
              </div>
              <div className="portal-feature-tag" style={{ color: "#b91c1c" }}>
                Automated Alert Routing <ArrowRight size={14} />
              </div>
            </div>

            {/* Card 6 */}
            <div className="portal-feature-card">
              <div>
                <div className="portal-icon-circle" style={{ background: "#06b6d4" }}>
                  <QrCode size={24} />
                </div>
                <h3 className="portal-feature-title">Traceability & Mobile Access</h3>
                <p className="portal-feature-text">
                  Use it anytime, anywhere on your mobile phone with barcode crop tagging, crate tracking, and simple Sinhala, Tamil, and English clarity.
                </p>
              </div>
              <div className="portal-feature-tag" style={{ color: "#0e7490" }}>
                Batch QR Code Generation <ArrowRight size={14} />
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------------
          HOW IT WORKS ("Simple Steps to Get Started")
          -------------------------------------------------------------------------- */}
      <section id="how-it-works" className="portal-steps-section">
        <div className="portal-container">
          <div style={{ textAlign: "center", marginBottom: "48px" }}>
            <div style={{ fontSize: "11px", fontWeight: 800, color: "#15803d", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>
              HOW IT WORKS
            </div>
            <h2 className="portal-section-title" style={{ textAlign: "center" }}>
              Simple Steps to Get Started
            </h2>
          </div>

          <div className="portal-steps-grid">

            <div className="portal-step-card">
              <div className="portal-step-num" style={{ background: "#15803d" }}>
                <Users size={24} />
              </div>
              <h3 className="portal-step-title">1. Sign Up</h3>
              <p className="portal-step-desc">
                Create your free farmer account in just a few minutes and choose your local district.
              </p>
            </div>

            <div className="portal-step-card">
              <div className="portal-step-num" style={{ background: "#f59e0b" }}>
                <MapPin size={24} />
              </div>
              <h3 className="portal-step-title">2. Set Your Location</h3>
              <p className="portal-step-desc">
                Select your agro-ecological zone and enter your intended crop, land size, and planting dates.
              </p>
            </div>

            <div className="portal-step-card">
              <div className="portal-step-num" style={{ background: "#3b82f6" }}>
                <BarChart3 size={24} />
              </div>
              <h3 className="portal-step-title">3. Explore Features</h3>
              <p className="portal-step-desc">
                Access pre-planting concentration risk analysis, price forecasts, and safe crop alternatives.
              </p>
            </div>

            <div className="portal-step-card">
              <div className="portal-step-num" style={{ background: "#166534" }}>
                <TrendingUp size={24} />
              </div>
              <h3 className="portal-step-title">4. Grow Better</h3>
              <p className="portal-step-desc">
                Make informed decisions, follow personalized schedules, and boost your harvest income.
              </p>
            </div>

          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------------
          SERVICES WE PROVIDE ("Our Services")
          -------------------------------------------------------------------------- */}
      <section id="services" className="portal-components-section">
        <div className="portal-container">
          <div style={{ textAlign: "center", maxWidth: "720px", margin: "0 auto 56px" }}>
            <div style={{ display: "inline-block", fontSize: "11px", fontWeight: 800, color: "#15803d", textTransform: "uppercase", letterSpacing: "1px", background: "#dcfce7", padding: "4px 14px", borderRadius: "9999px", marginBottom: "12px" }}>
              OUR SERVICES
            </div>
            <h2 className="portal-section-title" style={{ textAlign: "center" }}>
              Services We Provide
            </h2>
            <p style={{ fontSize: "15px", color: "#64748b", lineHeight: 1.6 }}>
              A complete AI-driven pipeline addressing fragmented agricultural processes across cultivation planning, market forecasting, produce tracking, and national early warning.
            </p>
          </div>

          <div className="portal-components-grid">
            {componentsData.map((item) => (
              <div key={item.id} className="portal-component-card">
                {/* Photo Top with Tag */}
                <div className="portal-card-img-wrap">
                  <img
                    src={item.image}
                    alt={item.title}
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  />
                  <div className="portal-card-badge" style={{ color: item.tagColor, backgroundColor: item.tagBg }}>
                    {item.badgeText}
                  </div>
                </div>

                <div className="portal-card-body">
                  <div>
                    <h3 className="portal-card-title">{item.shortTitle}</h3>
                    <p className="portal-card-text">{item.description}</p>
                  </div>

                  <div className="portal-card-actions">
                    <button
                      type="button"
                      onClick={() => setActiveModalComponent(item.id)}
                      className="portal-card-btn-spec"
                    >
                      <Info size={14} />
                      Research Specifications
                    </button>

                    {item.isLive ? (
                      <Link href={item.href} className="portal-card-btn-launch">
                        {item.actionText}
                        <ArrowRight size={14} />
                      </Link>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setActiveModalComponent(item.id)}
                        className="portal-card-btn-view"
                      >
                        {item.actionText}
                        <ChevronRight size={14} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------------
          RESEARCH CONTEXT, CLUSTERS & SDG IMPACT
          -------------------------------------------------------------------------- */}
      <section id="sdgs" className="portal-sdg-section">
        <div className="portal-container">
          <div className="portal-sdg-grid">

            {/* Left: Research Cluster & SDGs */}
            <div>
              <div className="portal-section-label">
                <span style={{ width: "20px", height: "2px", background: "#15803d", display: "inline-block" }} />
                SDG Alignment & Policy Impact
              </div>

              <h2 className="portal-section-title">
                Driving Sustainable Agricultural Impact in Sri Lanka
              </h2>

              <p className="portal-about-text">
                Aligned with the <strong>Artificial Intelligence, Data Science and Smart Systems</strong> cluster at the Faculty of Computing. The project addresses key industry verticals: Smart Agriculture, Agri-Supply Chain Management, Food Security, Climate Resilience, and Government Policy Support.
              </p>

              <div>
                <div className="portal-sdg-item">
                  <div className="portal-sdg-badge" style={{ background: "#fef3c7", color: "#b45309" }}>
                    2
                  </div>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#0f172a" }}>SDG 2: Zero Hunger</div>
                    <div style={{ fontSize: "12px", color: "#64748b" }}>
                      Improves pre-planting crop allocation, prevents harvest spoilage, and stabilizes national food supply.
                    </div>
                  </div>
                </div>

                <div className="portal-sdg-item">
                  <div className="portal-sdg-badge" style={{ background: "#dbeafe", color: "#1d4ed8" }}>
                    8
                  </div>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#0f172a" }}>SDG 8: Decent Work & Economic Growth</div>
                    <div style={{ fontSize: "12px", color: "#64748b" }}>
                      Reduces farmer financial risk, prevents market price collapses, and safeguards rural incomes.
                    </div>
                  </div>
                </div>

                <div className="portal-sdg-item">
                  <div className="portal-sdg-badge" style={{ background: "#dcfce7", color: "#166534" }}>
                    12
                  </div>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#0f172a" }}>SDG 12: Responsible Consumption</div>
                    <div style={{ fontSize: "12px", color: "#64748b" }}>
                      Minimizes post-harvest vegetable waste and routes spoiled produce into organic fertilizer & biogas.
                    </div>
                  </div>
                </div>

                <div className="portal-sdg-item">
                  <div className="portal-sdg-badge" style={{ background: "#ccfbf1", color: "#0f766e" }}>
                    13
                  </div>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#0f172a" }}>SDG 13: Climate Action</div>
                    <div style={{ fontSize: "12px", color: "#64748b" }}>
                      Integrates drought, flood, and reservoir early warning into agricultural pre-planting decisions.
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Technical Integration Architecture */}
            <div style={{ background: "#ffffff", padding: "36px", borderRadius: "28px", border: "1px solid #e2e8f0", boxShadow: "0 10px 25px rgba(0,0,0,0.04)" }}>
              <div style={{ borderBottom: "1px solid #f1f5f9", paddingBottom: "16px", marginBottom: "20px" }}>
                <div style={{ fontSize: "11px", fontWeight: 800, color: "#94a3b8", textTransform: "uppercase" }}>
                  System Architecture Pipeline
                </div>
                <h3 style={{ fontSize: "19px", fontWeight: 800, color: "#0f172a", margin: "4px 0 0" }}>
                  How the 4 Research Modules Work Together
                </h3>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", fontSize: "12px" }}>
                <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "16px", border: "1px solid #f1f5f9" }}>
                  <strong style={{ color: "#1e293b", display: "block", marginBottom: "4px" }}>
                    1. Market & Price AI
                  </strong>
                  <span style={{ color: "#64748b" }}>
                    ARIMA, LSTM, Prophet & XGBoost forecast future harvest prices & profit margins.
                  </span>
                </div>

                <div style={{ background: "#f0fdf4", padding: "16px", borderRadius: "16px", border: "1px solid #dcfce7" }}>
                  <strong style={{ color: "#14532d", display: "block", marginBottom: "4px" }}>
                    2. Concentration Risk
                  </strong>
                  <span style={{ color: "#166534" }}>
                    K-Means & DBSCAN cluster farmer intentions to prevent oversupply and generate schedules.
                  </span>
                </div>

                <div style={{ background: "#fffbeb", padding: "16px", borderRadius: "16px", border: "1px solid #fef3c7" }}>
                  <strong style={{ color: "#78350f", display: "block", marginBottom: "4px" }}>
                    3. Barcode & Waste
                  </strong>
                  <span style={{ color: "#92400e" }}>
                    QR crate tracking from farm to wholesale, converting damaged crops into organic bio-fertilizer.
                  </span>
                </div>

                <div style={{ background: "#faf5ff", padding: "16px", borderRadius: "16px", border: "1px solid #f3e8ff" }}>
                  <strong style={{ color: "#581c87", display: "block", marginBottom: "4px" }}>
                    4. National GIS Warning
                  </strong>
                  <span style={{ color: "#6b21a8" }}>
                    Reservoir, drought, and ENSO models route alerts directly to farmer crop plans.
                  </span>
                </div>
              </div>

              <div style={{ marginTop: "24px", background: "#0a2e18", color: "#ffffff", padding: "20px", borderRadius: "18px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px" }}>
                <div>
                  <div style={{ fontWeight: 800, fontSize: "14px" }}>Component 02 is Ready for Testing</div>
                  <div style={{ fontSize: "12px", color: "#86efac" }}>
                    Full pre-planting DBSCAN analysis, crop suggestions & guidelines available now.
                  </div>
                </div>
                <Link
                  href="/crop-planning"
                  style={{ background: "#22c55e", color: "#052e16", fontWeight: 800, fontSize: "12px", padding: "9px 18px", borderRadius: "10px", whiteSpace: "nowrap" }}
                >
                  Enter Portal
                </Link>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------------
          TESTIMONIALS SECTION (Matching Reference Screenshot)
          -------------------------------------------------------------------------- */}
      <section id="testimonials" className="portal-testimonials-section">
        <div className="portal-container">
          <div style={{ marginBottom: "44px" }}>
            <div style={{ fontSize: "11px", fontWeight: 800, color: "#15803d", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "6px" }}>
              — TESTIMONIALS
            </div>
            <h2 className="portal-section-title">
              What Farmers & Stakeholders Say
            </h2>
          </div>

          <div className="portal-testimonials-grid">

            <div className="portal-testimonial-card">
              <p className="portal-test-quote">
                &ldquo;AgroDecision AI has really helped me with pre-planting advice and market prices. I avoided oversupplied cabbage in Welimada and got 2.5x better returns for my crops.&rdquo;
              </p>
              <div className="portal-test-author">
                <div className="portal-test-avatar" style={{ background: "#15803d" }}>
                  RS
                </div>
                <div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a" }}>Ramesh Silva</div>
                  <div style={{ fontSize: "12px", color: "#64748b" }}>Vegetable Farmer, Badulla / Welimada</div>
                  <div style={{ display: "flex", gap: "2px", color: "#f59e0b", marginTop: "4px" }}>
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} size={13} style={{ fill: "#f59e0b" }} />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="portal-testimonial-card">
              <p className="portal-test-quote">
                &ldquo;The crop guidance feature and personalized cultivation calendar are amazing. I learned exactly when to apply fertilizer and had record yields this Yala season.&rdquo;
              </p>
              <div className="portal-test-author">
                <div className="portal-test-avatar" style={{ background: "#d97706" }}>
                  LM
                </div>
                <div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a" }}>Latha Menike</div>
                  <div style={{ fontSize: "12px", color: "#64748b" }}>Farmer, Nuwara Eliya</div>
                  <div style={{ display: "flex", gap: "2px", color: "#f59e0b", marginTop: "4px" }}>
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} size={13} style={{ fill: "#f59e0b" }} />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="portal-testimonial-card">
              <p className="portal-test-quote">
                &ldquo;Very easy to use and helpful system. The barcode batch tracking and spoiled crop composting recovery reduce economic centre wastage significantly.&rdquo;
              </p>
              <div className="portal-test-author">
                <div className="portal-test-avatar" style={{ background: "#2563eb" }}>
                  SW
                </div>
                <div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a" }}>Sunil Wickramasinghe</div>
                  <div style={{ fontSize: "12px", color: "#64748b" }}>Economic Centre Officer, Dambulla</div>
                  <div style={{ display: "flex", gap: "2px", color: "#f59e0b", marginTop: "4px" }}>
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} size={13} style={{ fill: "#f59e0b" }} />
                    ))}
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------------
          READY TO GET STARTED BANNER (Forest Green with Gold Button)
          -------------------------------------------------------------------------- */}
      <section className="portal-cta-wrap">
        <div className="portal-container">
          <div className="portal-cta-banner">
            <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
              <div style={{ width: "56px", height: "56px", borderRadius: "16px", background: "rgba(34, 197, 94, 0.2)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, border: "1px solid rgba(74, 222, 128, 0.3)" }}>
                <Sprout size={32} style={{ color: "#86efac" }} />
              </div>
              <div>
                <h3 style={{ fontSize: "24px", fontWeight: 800, margin: 0 }}>
                  Ready to Get Started?
                </h3>
                <p style={{ fontSize: "14px", color: "#bbf7d0", margin: "6px 0 0" }}>
                  Join thousands of farmers who are already growing better with AgroDecision AI. Your success is our mission.
                </p>
              </div>
            </div>

            <Link href="/crop-planning/register" className="portal-btn-gold">
              Get Started <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------------
          FOOTER (Kishan Sathi Exact Format)
          -------------------------------------------------------------------------- */}
      <footer className="portal-footer">
        <div className="portal-container">
          <div className="portal-footer-grid">

            {/* Col 1 */}
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
                <div style={{ width: "38px", height: "38px", borderRadius: "10px", background: "#15803d", display: "flex", alignItems: "center", justifyContent: "center", color: "#ffffff" }}>
                  <Sprout size={22} />
                </div>
                <div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "#ffffff" }}>AgroDecision AI</div>
                  <div style={{ fontSize: "11px", color: "#4ade80" }}>Better Farmers • Brighter Future</div>
                </div>
              </div>
              <p style={{ fontSize: "13px", lineHeight: 1.65, color: "#94a3b8", marginBottom: "16px" }}>
                Data-Driven Farmer Decision System for Collaborative Crop Planning and Market Risk Reduction.
              </p>
              <div style={{ fontSize: "12px", color: "#cbd5e1" }}>
                <strong>AIMS</strong> - Autonomous Intelligent Machines and Systems
                <br />Faculty of Computing • Information Technology (IT)
              </div>
            </div>

            {/* Col 2 */}
            <div className="portal-footer-col">
              <h4>Quick Links</h4>
              <ul>
                <li><a href="#hero">Home</a></li>
                <li><a href="#about">About Us</a></li>
                <li><a href="#features">Key Features</a></li>
                <li><a href="#services">Our Services</a></li>
                <li><Link href="/crop-planning/login">Farmer Login</Link></li>
              </ul>
            </div>

            {/* Col 3 */}
            <div className="portal-footer-col">
              <h4>Research Modules</h4>
              <ul>
                <li>
                  <Link href="/crop-planning" style={{ color: "#4ade80", fontWeight: 700 }}>
                    Component 02: Crop Planning (Live)
                  </Link>
                </li>
                <li>
                  <button type="button" onClick={() => setActiveModalComponent(1)}>
                    Component 01: Market Profit AI
                  </button>
                </li>
                <li>
                  <button type="button" onClick={() => setActiveModalComponent(3)}>
                    Component 03: Produce Traceability & Waste
                  </button>
                </li>
                <li>
                  <button type="button" onClick={() => setActiveModalComponent(4)}>
                    Component 04: Climate GIS Early Warning
                  </button>
                </li>
              </ul>
            </div>

            {/* Col 4 */}
            <div className="portal-footer-col">
              <h4>Contact & Support</h4>
              <div style={{ fontSize: "13px", lineHeight: 1.8, color: "#94a3b8" }}>
                <div>+94 (0) 11 234 5678 / Support</div>
                <div>aims.research@agrodecision.lk</div>
                <div style={{ marginTop: "6px" }}>
                  Faculty of Computing, Sri Lanka
                </div>
              </div>
            </div>

          </div>

          {/* Bottom Bar */}
          <div style={{ paddingTop: "28px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", fontSize: "12px", color: "#64748b" }}>
            <div>© 2026 AgroDecision AI. All rights reserved.</div>
            <div style={{ color: "#4ade80", fontWeight: 600 }}>
              Grow Together • Farmer • Technology • Prosperity 🌾
            </div>
          </div>
        </div>
      </footer>

      {/* --------------------------------------------------------------------------
          RESEARCH COMPONENT DETAILS MODAL
          -------------------------------------------------------------------------- */}
      {activeModalComponent !== null && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 100,
            backgroundColor: "rgba(0, 0, 0, 0.65)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          {(() => {
            const comp = componentsData.find((c) => c.id === activeModalComponent);
            if (!comp) return null;
            return (
              <div
                style={{
                  background: "#ffffff",
                  borderRadius: "28px",
                  maxWidth: "680px",
                  width: "100%",
                  maxHeight: "90vh",
                  overflowY: "auto",
                  padding: "32px",
                  boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
                  position: "relative",
                  border: "1px solid #e2e8f0",
                }}
              >
                {/* Close Button */}
                <button
                  type="button"
                  onClick={() => setActiveModalComponent(null)}
                  style={{
                    position: "absolute",
                    top: "20px",
                    right: "20px",
                    background: "#f1f5f9",
                    border: "none",
                    borderRadius: "50%",
                    width: "36px",
                    height: "36px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    color: "#475569",
                  }}
                  aria-label="Close modal"
                >
                  <X size={18} />
                </button>

                <div style={{ marginBottom: "16px" }}>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 800,
                      padding: "4px 10px",
                      borderRadius: "9999px",
                      background: comp.tagBg,
                      color: comp.tagColor,
                      textTransform: "uppercase",
                    }}
                  >
                    {comp.category}
                  </span>
                  <h3
                    style={{
                      fontSize: "22px",
                      fontWeight: 800,
                      color: "#0f172a",
                      margin: "10px 0 0",
                      lineHeight: 1.3,
                    }}
                  >
                    {comp.title}
                  </h3>
                </div>

                <div
                  style={{
                    position: "relative",
                    width: "100%",
                    height: "200px",
                    borderRadius: "18px",
                    overflow: "hidden",
                    marginBottom: "20px",
                  }}
                >
                  <img
                    src={comp.image}
                    alt={comp.title}
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  />
                </div>

                <div
                  style={{
                    background: "#f0fdf4",
                    border: "1px solid #bbf7d0",
                    padding: "16px",
                    borderRadius: "16px",
                    marginBottom: "18px",
                  }}
                >
                  <strong style={{ fontSize: "12px", color: "#166534", textTransform: "uppercase", display: "block", marginBottom: "4px" }}>
                    How It Addresses Research Gaps:
                  </strong>
                  <p style={{ fontSize: "13px", color: "#15803d", margin: 0, lineHeight: 1.55 }}>
                    {comp.gapAddressed}
                  </p>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "18px" }}>
                  <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "16px", border: "1px solid #f1f5f9" }}>
                    <strong style={{ fontSize: "12px", color: "#0f172a", textTransform: "uppercase", display: "block", marginBottom: "8px" }}>
                      Key Inputs:
                    </strong>
                    <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "12px", color: "#475569", lineHeight: 1.6 }}>
                      {comp.inputs.map((inp, idx) => (
                        <li key={idx}>{inp}</li>
                      ))}
                    </ul>
                  </div>

                  <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "16px", border: "1px solid #f1f5f9" }}>
                    <strong style={{ fontSize: "12px", color: "#0f172a", textTransform: "uppercase", display: "block", marginBottom: "8px" }}>
                      Expected Outputs:
                    </strong>
                    <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "12px", color: "#475569", lineHeight: 1.6 }}>
                      {comp.outputs.map((out, idx) => (
                        <li key={idx}>{out}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "16px", border: "1px solid #f1f5f9", marginBottom: "24px" }}>
                  <strong style={{ fontSize: "12px", color: "#0f172a", textTransform: "uppercase", display: "block", marginBottom: "4px" }}>
                    Methodology & Machine Learning Models:
                  </strong>
                  <p style={{ fontSize: "12.5px", color: "#475569", margin: 0, lineHeight: 1.6 }}>
                    {comp.process}
                  </p>
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
                  <button
                    type="button"
                    onClick={() => setActiveModalComponent(null)}
                    style={{
                      padding: "10px 20px",
                      borderRadius: "12px",
                      background: "#f1f5f9",
                      border: "none",
                      color: "#475569",
                      fontSize: "13px",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Close
                  </button>

                  {comp.isLive ? (
                    <Link
                      href={comp.href}
                      style={{
                        padding: "10px 24px",
                        borderRadius: "12px",
                        background: "#15803d",
                        color: "#ffffff",
                        fontSize: "13px",
                        fontWeight: 700,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      Open Live Module <ArrowRight size={14} />
                    </Link>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setActiveModalComponent(null)}
                      style={{
                        padding: "10px 24px",
                        borderRadius: "12px",
                        background: "#0f172a",
                        color: "#ffffff",
                        fontSize: "13px",
                        fontWeight: 700,
                        border: "none",
                        cursor: "pointer",
                      }}
                    >
                      Specifications Reviewed
                    </button>
                  )}
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}
