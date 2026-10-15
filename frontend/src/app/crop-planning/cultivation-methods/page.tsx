"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Calendar,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock,
  Download,
  Droplets,
  Leaf,
  Lightbulb,
  ShieldCheck,
  Sprout,
} from "lucide-react";
import { useSession } from "../components/session";
import { useLoad } from "../components/ui";
import { formatDate } from "../lib/dates";
import type { Plan } from "../lib/contracts";

const CROPS_LIST = [
  { name: "Bandakka", label: "Bandakka (Okra)", icon: "🌿", image: "/images/crop_okra_detail.jpg" },
  { name: "Brinjal", label: "Brinjal", icon: "🍆", image: "/images/crop_brinjal_detail.jpg" },
  { name: "Corn", label: "Corn (Maize)", icon: "🌽", image: "/images/crop_corn_detail.jpg" },
  { name: "Chillies", label: "Chillies", icon: "🌶️", image: "/images/crop_chili_detail.jpg" },
  { name: "Mung Beans", label: "Mung Beans", icon: "🌱", image: "/images/crop_mungbean_detail.jpg" },
  { name: "Pumpkin", label: "Pumpkin", icon: "🎃", image: "/images/crop_pumpkin_detail.jpg" },
];

interface StageInfo {
  id: string;
  title: string;
  offsetStartDays: number;
  offsetEndDays: number;
  status: "Completed" | "Current Stage" | "Upcoming";
  image: string;
  guidance: string[];
  notes: string;
}

interface CropAgronomicData {
  commonName: string;
  durationDays: number;
  method: string;
  spacing: string;
  season: string;
  inputRequirements: {
    manureTonsPerAcre: number;
    basalUreaKg: number;
    basalTspKg: number;
    basalMopKg: number;
    topDressingUreaKg: number;
    irrigationNote: string;
  };
  stages: StageInfo[];
}

const CROP_GUIDANCE: Record<string, CropAgronomicData> = {
  Bandakka: {
    commonName: "Bandakka (Okra)",
    durationDays: 95,
    method: "Direct Sowing",
    spacing: "90 cm × 60 cm",
    season: "Maha / Yala",
    inputRequirements: {
      manureTonsPerAcre: 6,
      basalUreaKg: 30,
      basalTspKg: 45,
      basalMopKg: 25,
      topDressingUreaKg: 30,
      irrigationNote: "Regular watering every 4–6 days; avoid waterlogging.",
    },
    stages: [
      {
        id: "land-prep",
        title: "Land Preparation",
        offsetStartDays: -14,
        offsetEndDays: -1,
        status: "Completed",
        image: "/images/field_furrows_detail.jpg",
        guidance: [
          "Plough the land to a depth of 20–25 cm for optimal root penetration.",
          "Harrow twice to obtain a fine, weed-free soil tilth.",
          "Form raised beds or ridges to ensure fast drainage during heavy rains.",
          "Incorporate well-decomposed organic manure thoroughly into the soil.",
        ],
        notes: "Apply organic manure at least 7–10 days before sowing for best nutrient release.",
      },
      {
        id: "planting",
        title: "Planting / Sowing",
        offsetStartDays: 0,
        offsetEndDays: 5,
        status: "Current Stage",
        image: "/images/crop_okra_detail.jpg",
        guidance: [
          "Direct sow 3–4 seeds per pit at a depth of 2–3 cm.",
          "Maintain row spacing of 90 cm and plant-to-plant spacing of 60 cm.",
          "Apply basal NPK fertilizer mix around each pit and lightly cover.",
          "Give a light irrigation immediately after sowing.",
        ],
        notes: "Soaking seeds in lukewarm water for 12 hours improves uniform germination.",
      },
      {
        id: "vegetative",
        title: "Vegetative Growth & Weeding",
        offsetStartDays: 6,
        offsetEndDays: 35,
        status: "Upcoming",
        image: "/images/field_furrows_detail.jpg",
        guidance: [
          "Thin out excess seedlings at 10–14 days, retaining the 2 healthiest plants per pit.",
          "Perform first shallow weeding and earthing up at 3 weeks after germination.",
          "Apply 1st top dressing of Nitrogen (Urea) at 4 weeks.",
          "Monitor foliage for flea beetles and yellow vein mosaic symptoms.",
        ],
        notes: "Earthing up supports the tall okra stems against strong winds.",
      },
      {
        id: "flowering",
        title: "Flowering Stage",
        offsetStartDays: 36,
        offsetEndDays: 50,
        status: "Upcoming",
        image: "/images/crop_okra_detail.jpg",
        guidance: [
          "Yellow hibiscus-like blossoms appear; ensure adequate moisture for bloom retention.",
          "Apply 2nd top dressing of Urea along with irrigation.",
          "Scout for fruit borers and aphids in the tender flowers.",
        ],
        notes: "Avoid water stress during peak blooming to prevent blossom drop.",
      },
      {
        id: "fruiting",
        title: "Pod Development",
        offsetStartDays: 51,
        offsetEndDays: 70,
        status: "Upcoming",
        image: "/images/crop_okra_detail.jpg",
        guidance: [
          "Pods expand rapidly and reach tender edible stage within 5–6 days of flowering.",
          "Maintain consistent soil moisture for tender, non-fibrous pods.",
          "Maintain clean furrows for easy access during picking.",
        ],
        notes: "Over-mature pods turn woody and fibrous, severely lowering market price.",
      },
      {
        id: "harvesting",
        title: "Harvesting & Picking",
        offsetStartDays: 71,
        offsetEndDays: 95,
        status: "Upcoming",
        image: "/images/crop_okra_detail.jpg",
        guidance: [
          "Harvest pods when they are tender, bright green, and 7–10 cm long.",
          "Repeat harvest every 2–3 days to stimulate continued flowering and yield.",
          "Use a sharp knife or shears; do not pull violently on stems.",
          "Pack in ventilated crates away from direct sunlight for market delivery.",
        ],
        notes: "Regular picking extends the harvest season by up to 30 additional days.",
      },
    ],
  },
  Brinjal: {
    commonName: "Brinjal (Eggplant)",
    durationDays: 110,
    method: "Transplanting",
    spacing: "90 cm × 60 cm",
    season: "Maha / Yala",
    inputRequirements: {
      manureTonsPerAcre: 8,
      basalUreaKg: 40,
      basalTspKg: 60,
      basalMopKg: 35,
      topDressingUreaKg: 35,
      irrigationNote: "Irrigate every 4–5 days; maintain soil moisture during fruit development.",
    },
    stages: [
      {
        id: "land-prep",
        title: "Land Preparation",
        offsetStartDays: -14,
        offsetEndDays: -1,
        status: "Completed",
        image: "/images/field_furrows_detail.jpg",
        guidance: [
          "Plough deep and harrow twice to create a crumbly, fertile seedbed.",
          "Incorporate 8 tons of organic compost per acre for root aeration.",
          "Prepare ridges spaced 90 cm apart for easy water movement.",
        ],
        notes: "Brinjal thrives best in well-drained loamy soil with neutral pH (5.5–6.8).",
      },
      {
        id: "planting",
        title: "Transplanting",
        offsetStartDays: 0,
        offsetEndDays: 5,
        status: "Current Stage",
        image: "/images/crop_brinjal_detail.jpg",
        guidance: [
          "Transplant 30–35 day old robust nursery seedlings with 4–5 true leaves.",
          "Space seedlings 60 cm apart along ridges spaced 90 cm apart.",
          "Transplant during late afternoon to prevent wilting from heat shock.",
          "Water seedlings immediately after transplanting.",
        ],
        notes: "Hardening seedlings in the nursery by reducing water 3 days prior improves field survival.",
      },
      {
        id: "vegetative",
        title: "Vegetative & Earthing Up",
        offsetStartDays: 6,
        offsetEndDays: 40,
        status: "Upcoming",
        image: "/images/field_furrows_detail.jpg",
        guidance: [
          "Perform 1st weeding and light earthing up at 3 weeks.",
          "Apply 1st top dressing of Urea around each plant root zone.",
          "Inspect plant tips for shoot borer wilting.",
        ],
        notes: "Pruning diseased or dried lower leaves improves air flow and reduces fungal rot.",
      },
      {
        id: "flowering",
        title: "Flowering Stage",
        offsetStartDays: 41,
        offsetEndDays: 65,
        status: "Upcoming",
        image: "/images/crop_brinjal_detail.jpg",
        guidance: [
          "Abundant purple blossoms appear; maintain moderate, steady moisture.",
          "Apply 2nd top dressing of Urea and Potassium for firm fruit skin.",
          "Install pheromone traps for integrated pest management (IPM).",
        ],
        notes: "Avoid overhead irrigation during flowering to allow insect pollination.",
      },
      {
        id: "fruiting",
        title: "Fruit Expansion",
        offsetStartDays: 66,
        offsetEndDays: 80,
        status: "Upcoming",
        image: "/images/crop_brinjal_detail.jpg",
        guidance: [
          "Eggplants expand and develop high gloss and characteristic coloration.",
          "Support heavily bearing branches with light bamboo stakes if needed.",
        ],
        notes: "Harvest before seeds turn hard and skin loses glossy sheen.",
      },
      {
        id: "harvesting",
        title: "Continuous Harvesting",
        offsetStartDays: 81,
        offsetEndDays: 110,
        status: "Upcoming",
        image: "/images/crop_brinjal_detail.jpg",
        guidance: [
          "Harvest tender, glossy fruits with green calyx intact using pruning shears.",
          "Repeat harvest every 4–6 days across the harvesting window.",
          "Grade by size and pack gently into cushioned plastic crates.",
        ],
        notes: "Do not leave over-ripe fruits on vines as they halt new flower production.",
      },
    ],
  },
  Corn: {
    commonName: "Corn (Maize)",
    durationDays: 100,
    method: "Direct Sowing",
    spacing: "60 cm × 25 cm",
    season: "Maha / Yala",
    inputRequirements: {
      manureTonsPerAcre: 5,
      basalUreaKg: 40,
      basalTspKg: 50,
      basalMopKg: 30,
      topDressingUreaKg: 50,
      irrigationNote: "High water requirement during tasseling and grain filling.",
    },
    stages: [
      {
        id: "land-prep",
        title: "Land Preparation",
        offsetStartDays: -10,
        offsetEndDays: -1,
        status: "Completed",
        image: "/images/field_furrows_detail.jpg",
        guidance: [
          "Plough 20 cm deep and harrow to break clods for good root anchorage.",
          "Make furrows spaced 60 cm apart along contour lines.",
          "Incorporate basal fertilizer into the planting furrows.",
        ],
        notes: "Good drainage is essential; maize cannot tolerate stagnant water.",
      },
      {
        id: "planting",
        title: "Sowing",
        offsetStartDays: 0,
        offsetEndDays: 4,
        status: "Current Stage",
        image: "/images/crop_corn_detail.jpg",
        guidance: [
          "Sow seeds 2–3 cm deep at 25 cm spacing along furrows.",
          "Ensure soil has sufficient moisture at sowing time.",
          "Cover with loose topsoil and firm gently.",
        ],
        notes: "Seed treatment with bio-fungicide prevents early seedling rot.",
      },
      {
        id: "vegetative",
        title: "Knee-High Stage",
        offsetStartDays: 5,
        offsetEndDays: 35,
        status: "Upcoming",
        image: "/images/field_furrows_detail.jpg",
        guidance: [
          "Weed and earth up soil around stems when plants reach knee height (~30 days).",
          "Apply top dressing of Urea along with irrigation.",
          "Scout leaf whorls for Fall Armyworm caterpillars.",
        ],
        notes: "Earthing up prevents lodging when stalks grow tall.",
      },
      {
        id: "flowering",
        title: "Tasseling & Silking",
        offsetStartDays: 36,
        offsetEndDays: 60,
        status: "Upcoming",
        image: "/images/crop_corn_detail.jpg",
        guidance: [
          "Tassels shed pollen onto silks; water stress during this 2-week period cuts yield by 50%.",
          "Ensure regular furrow irrigation.",
        ],
        notes: "Adequate pollination requires breeze across dense row plantings.",
      },
      {
        id: "fruiting",
        title: "Grain Filling",
        offsetStartDays: 61,
        offsetEndDays: 80,
        status: "Upcoming",
        image: "/images/crop_corn_detail.jpg",
        guidance: [
          "Kernels progress from milk to dough stage.",
          "Scare birds from feeding on tender immature ears.",
        ],
        notes: "Irrigation can be gradually tapered off as silks dry completely.",
      },
      {
        id: "harvesting",
        title: "Cob Harvest",
        offsetStartDays: 81,
        offsetEndDays: 100,
        status: "Upcoming",
        image: "/images/crop_corn_detail.jpg",
        guidance: [
          "Harvest when husk leaves turn straw-yellow and kernels dent firmly.",
          "Snap cobs cleanly downwards from the stalk.",
          "Dry cobs in sunny yards to 12% moisture for safe grain storage.",
        ],
        notes: "Immediate de-husking and sun drying prevents fungal aflatoxin contamination.",
      },
    ],
  },
  Chillies: {
    commonName: "Chillies",
    durationDays: 120,
    method: "Transplanting",
    spacing: "60 cm × 45 cm",
    season: "Maha / Yala",
    inputRequirements: {
      manureTonsPerAcre: 8,
      basalUreaKg: 35,
      basalTspKg: 55,
      basalMopKg: 30,
      topDressingUreaKg: 30,
      irrigationNote: "Light, frequent watering; avoid water stagnation which causes root rot.",
    },
    stages: [
      {
        id: "land-prep",
        title: "Land Preparation",
        offsetStartDays: -14,
        offsetEndDays: -1,
        status: "Completed",
        image: "/images/field_furrows_detail.jpg",
        guidance: [
          "Deep plough and create 15 cm high raised beds.",
          "Incorporate 8–10 tons of decomposed organic manure per acre.",
          "Mix basal NPK thoroughly into planting pits.",
        ],
        notes: "Raised beds prevent collar rot and bacterial wilt.",
      },
      {
        id: "planting",
        title: "Transplanting",
        offsetStartDays: 0,
        offsetEndDays: 5,
        status: "Current Stage",
        image: "/images/crop_chili_detail.jpg",
        guidance: [
          "Transplant 30–35 day old nursery seedlings with pencil-thick stems.",
          "Space plants 45 cm apart in rows spaced 60 cm apart.",
          "Water seedlings immediately with a fine rose sprinkler.",
        ],
        notes: "Transplant on cloudy days or late afternoon to minimize transplanting shock.",
      },
      {
        id: "vegetative",
        title: "Branching & Weeding",
        offsetStartDays: 6,
        offsetEndDays: 45,
        status: "Upcoming",
        image: "/images/field_furrows_detail.jpg",
        guidance: [
          "Perform shallow manual weeding at 2 and 4 weeks.",
          "Apply 1st top dressing of Urea at 3 weeks.",
          "Inspect leaf undersides for thrips and mites (leaf curl prevention).",
        ],
        notes: "Yellow sticky traps help monitor and control sucking thrip pests.",
      },
      {
        id: "flowering",
        title: "Flowering Stage",
        offsetStartDays: 46,
        offsetEndDays: 70,
        status: "Upcoming",
        image: "/images/crop_chili_detail.jpg",
        guidance: [
          "Flowers emerge at stem forks; avoid overhead irrigation during bloom.",
          "Apply 2nd top dressing with Potassium to boost pod firmness and color.",
        ],
        notes: "Consistent root moisture prevents flower drop.",
      },
      {
        id: "fruiting",
        title: "Pod Setting",
        offsetStartDays: 71,
        offsetEndDays: 85,
        status: "Upcoming",
        image: "/images/crop_chili_detail.jpg",
        guidance: [
          "Green pods develop rapidly and attain full size and pungency.",
          "Check for anthracnose fruit rot spots during rainy spells.",
        ],
        notes: "Support heavy plants with low stakes if fruiting branches droop.",
      },
      {
        id: "harvesting",
        title: "Multi-Pick Harvest",
        offsetStartDays: 86,
        offsetEndDays: 120,
        status: "Upcoming",
        image: "/images/crop_chili_detail.jpg",
        guidance: [
          "Harvest firm, shiny green chillies or allow to ripen fully to red.",
          "Pick with fruit stalk intact every 7–10 days.",
          "Spread red chillies on clean tarpaulins for sun drying.",
        ],
        notes: "Regular picking encourages new vegetative flushes and continuous flower buds.",
      },
    ],
  },
  "Mung Beans": {
    commonName: "Mung Beans (Green Gram)",
    durationDays: 70,
    method: "Direct Sowing",
    spacing: "30 cm × 10 cm",
    season: "Yala / Maha",
    inputRequirements: {
      manureTonsPerAcre: 3,
      basalUreaKg: 15,
      basalTspKg: 35,
      basalMopKg: 15,
      topDressingUreaKg: 0,
      irrigationNote: "Drought hardy; needs only 2–3 light irrigations throughout life cycle.",
    },
    stages: [
      {
        id: "land-prep",
        title: "Land Preparation",
        offsetStartDays: -7,
        offsetEndDays: -1,
        status: "Completed",
        image: "/images/field_furrows_detail.jpg",
        guidance: [
          "Light ploughing or zero-tillage relay cropping after paddy harvest.",
          "Level the surface to avoid any stagnant water puddles.",
        ],
        notes: "Mung bean roots fix atmospheric nitrogen, requiring minimal synthetic fertilizer.",
      },
      {
        id: "planting",
        title: "Sowing",
        offsetStartDays: 0,
        offsetEndDays: 3,
        status: "Current Stage",
        image: "/images/crop_mungbean_detail.jpg",
        guidance: [
          "Sow seeds in shallow lines 30 cm apart, 10 cm between seeds.",
          "Inoculate seeds with Rhizobium culture before sowing.",
          "Ensure good residual soil moisture for swift germination.",
        ],
        notes: "Seeds sprout rapidly within 3–4 days.",
      },
      {
        id: "vegetative",
        title: "Canopy Closure",
        offsetStartDays: 4,
        offsetEndDays: 25,
        status: "Upcoming",
        image: "/images/field_furrows_detail.jpg",
        guidance: [
          "Perform one hand weeding at 15–18 days before canopy completely covers soil.",
          "Monitor for bean fly seedling damage.",
        ],
        notes: "Dense canopy suppresses weed growth naturally after 3 weeks.",
      },
      {
        id: "flowering",
        title: "Flowering Stage",
        offsetStartDays: 26,
        offsetEndDays: 42,
        status: "Upcoming",
        image: "/images/crop_mungbean_detail.jpg",
        guidance: [
          "Yellow blossoms open synchronously across the field.",
          "Provide one light irrigation if soil is dry during pod setting.",
        ],
        notes: "Avoid chemical sprays during peak morning bee activity.",
      },
      {
        id: "fruiting",
        title: "Pod Maturation",
        offsetStartDays: 43,
        offsetEndDays: 55,
        status: "Upcoming",
        image: "/images/crop_mungbean_detail.jpg",
        guidance: [
          "Cylindrical pods develop and turn from bright green to dark brown/black.",
        ],
        notes: "Stop all irrigation when pods begin darkening to promote uniform drying.",
      },
      {
        id: "harvesting",
        title: "Pod Picking",
        offsetStartDays: 56,
        offsetEndDays: 70,
        status: "Upcoming",
        image: "/images/crop_mungbean_detail.jpg",
        guidance: [
          "Hand-pick dry black pods in the early morning before pods shatter in the sun.",
          "A second picking can be done 7–10 days later for late-formed pods.",
          "Thresh pods on a clean floor and winnow seeds to remove chaff.",
        ],
        notes: "Fast 70-day cash return makes Mung Beans an ideal alternative crop.",
      },
    ],
  },
  Pumpkin: {
    commonName: "Pumpkin",
    durationDays: 105,
    method: "Basin Pits",
    spacing: "2.5 m × 2.0 m",
    season: "Maha / Yala",
    inputRequirements: {
      manureTonsPerAcre: 7,
      basalUreaKg: 30,
      basalTspKg: 50,
      basalMopKg: 35,
      topDressingUreaKg: 25,
      irrigationNote: "Irrigate basin pits weekly; keep leaves and developing fruit dry.",
    },
    stages: [
      {
        id: "land-prep",
        title: "Basin Preparation",
        offsetStartDays: -10,
        offsetEndDays: -1,
        status: "Completed",
        image: "/images/field_furrows_detail.jpg",
        guidance: [
          "Dig pits 1 meter in diameter and 30 cm deep spaced 2.5 meters apart.",
          "Mix topsoil with 10 kg of organic manure and basal fertilizer per pit.",
          "Form slightly raised basin mounds to avoid waterlogging around vine roots.",
        ],
        notes: "Wide spacing allows sprawling vine expansion without overcrowding.",
      },
      {
        id: "planting",
        title: "Direct Sowing in Pits",
        offsetStartDays: 0,
        offsetEndDays: 4,
        status: "Current Stage",
        image: "/images/crop_pumpkin_detail.jpg",
        guidance: [
          "Sow 4–5 seeds per pit at 2–3 cm depth.",
          "Water thoroughly after sowing.",
          "Thin to the 3 most vigorous vines per pit after 12 days.",
        ],
        notes: "Soaking seeds overnight accelerates strong taproot emergence.",
      },
      {
        id: "vegetative",
        title: "Vine Running & Training",
        offsetStartDays: 5,
        offsetEndDays: 40,
        status: "Upcoming",
        image: "/images/field_furrows_detail.jpg",
        guidance: [
          "Train creeping vines evenly over the field surface.",
          "Apply top dressing of Urea around pit perimeter at 4 weeks.",
          "Mulch around basins with straw to conserve moisture and suppress weeds.",
        ],
        notes: "Mulching keeps developing fruit off damp ground, preventing soil rot.",
      },
      {
        id: "flowering",
        title: "Flowering & Pollination",
        offsetStartDays: 41,
        offsetEndDays: 60,
        status: "Upcoming",
        image: "/images/crop_pumpkin_detail.jpg",
        guidance: [
          "Large yellow male and female flowers bloom; bees perform natural pollination.",
          "Maintain weekly pit irrigation.",
        ],
        notes: "Female flowers have a tiny immature pumpkin at the base of the petals.",
      },
      {
        id: "fruiting",
        title: "Fruit Expansion",
        offsetStartDays: 61,
        offsetEndDays: 85,
        status: "Upcoming",
        image: "/images/crop_pumpkin_detail.jpg",
        guidance: [
          "Pumpkins gain size and heavy weight.",
          "Turn fruit gently once or twice for uniform skin color and round shape.",
        ],
        notes: "Do not move vines violently once fruits have set.",
      },
      {
        id: "harvesting",
        title: "Maturity Harvest",
        offsetStartDays: 86,
        offsetEndDays: 105,
        status: "Upcoming",
        image: "/images/crop_pumpkin_detail.jpg",
        guidance: [
          "Harvest when fruit stem turns hard and corky, and rind resists thumbnail puncture.",
          "Cut stem cleanly leaving a 5 cm handle attached to the fruit.",
          "Cure harvested pumpkins in dry shade for 10 days for long shelf storage.",
        ],
        notes: "Pumpkins can be stored for 2–3 months without spoilage, ensuring flexible market sales.",
      },
    ],
  },
};

export default function CultivationMethodsPage() {
  const { api } = useSession();
  const [selectedCrop, setSelectedCrop] = useState<string>("Bandakka");
  const [selectedPlanId, setSelectedPlanId] = useState<string>("");
  const [selectedStageId, setSelectedStageId] = useState<string>("land-prep");
  const [timelineView, setTimelineView] = useState<"timeline" | "calendar">("timeline");

  const plansResult = useLoad(
    (signal) => api.list(new URLSearchParams({ limit: "20", status: "active" }), signal),
    [api]
  );

  const plans: Plan[] = useMemo(() => plansResult.data?.items ?? [], [plansResult.data?.items]);

  const matchingPlan = useMemo(() => {
    if (selectedPlanId) return plans.find((p) => p.plan_id === selectedPlanId) || null;
    return plans.find((p) => p.crop === selectedCrop) || null;
  }, [plans, selectedPlanId, selectedCrop]);

  const activeCropData = CROP_GUIDANCE[selectedCrop] || CROP_GUIDANCE.Bandakka;
  const plantingDate = matchingPlan?.planting_date ? new Date(matchingPlan.planting_date) : new Date();
  const acres = matchingPlan?.land_size_acres || 1;

  const addDays = (d: Date, days: number): Date => {
    const res = new Date(d);
    res.setDate(res.getDate() + days);
    return res;
  };

  const formatShortDate = (d: Date): string => {
    return d.toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" });
  };

  const dynamicStages = useMemo(() => {
    return activeCropData.stages.map((stage) => {
      const start = addDays(plantingDate, stage.offsetStartDays);
      const end = addDays(plantingDate, stage.offsetEndDays);
      return {
        ...stage,
        formattedRange: `${formatShortDate(start)} – ${formatShortDate(end)}`,
      };
    });
  }, [activeCropData, plantingDate]);

  const activeStage = dynamicStages.find((s) => s.id === selectedStageId) || dynamicStages[0];
  const req = activeCropData.inputRequirements;

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto", paddingBottom: "60px" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "16px",
          marginBottom: "20px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "14px",
              background: "#eaf5ea",
              color: "#15803d",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <Calendar size={26} />
          </div>
          <div>
            <h1 style={{ fontSize: "26px", fontWeight: 800, color: "#0f172a", margin: 0, letterSpacing: "-0.02em" }}>
              Your Cultivation Plan
            </h1>
            <p style={{ fontSize: "13.5px", color: "#64748b", margin: "4px 0 0 0" }}>
              Get personalized cultivation guidance for your selected crop based on research-backed agronomic practices for your region and season.
            </p>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            padding: "10px 18px",
            background: "#f0fdf4",
            border: "1px solid #bbf7d0",
            borderRadius: "14px",
          }}
        >
          <Sprout size={22} style={{ color: "#16a34a" }} />
          <div>
            <strong style={{ fontSize: "12.5px", color: "#14532d", display: "block" }}>Plan well,</strong>
            <span style={{ fontSize: "11.5px", color: "#15803d" }}>Grow sustainably for a better tomorrow.</span>
          </div>
        </div>
      </div>

      {/* 6 Crops Selector Bar */}
      <div
        style={{
          background: "#ffffff",
          borderRadius: "18px",
          padding: "12px",
          border: "1px solid #e2e8f0",
          boxShadow: "0 2px 8px rgba(0,0,0,0.02)",
          marginBottom: "24px",
        }}
      >
        <span style={{ fontSize: "11px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", paddingLeft: "8px", display: "block", marginBottom: "8px" }}>
          Select a Crop:
        </span>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "10px" }}>
          {CROPS_LIST.map((crop) => {
            const isSelected = selectedCrop === crop.name;
            return (
              <button
                key={crop.name}
                onClick={() => {
                  setSelectedCrop(crop.name);
                  setSelectedStageId("land-prep");
                  setSelectedPlanId("");
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  padding: "12px 14px",
                  borderRadius: "12px",
                  background: isSelected ? "#15803d" : "#f8fafc",
                  color: isSelected ? "#ffffff" : "#1e293b",
                  border: isSelected ? "1px solid #15803d" : "1px solid #e2e8f0",
                  cursor: "pointer",
                  fontWeight: isSelected ? 700 : 600,
                  fontSize: "13px",
                  transition: "all 0.2s",
                }}
              >
                <span>{crop.icon}</span>
                <span>{crop.name}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Plan Personalization Context */}
      {plans.length > 0 && (
        <div
          style={{
            background: "#f0fdf4",
            borderRadius: "14px",
            border: "1px solid #bbf7d0",
            padding: "12px 18px",
            marginBottom: "24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Sprout size={18} style={{ color: "#16a34a" }} />
            <span style={{ fontSize: "13px", color: "#14532d" }}>
              Personalize with your registered plan:
            </span>
            <select
              value={matchingPlan?.plan_id || ""}
              onChange={(e) => {
                const found = plans.find((p) => p.plan_id === e.target.value);
                if (found) {
                  setSelectedCrop(found.crop);
                  setSelectedPlanId(found.plan_id);
                  setSelectedStageId("land-prep");
                } else {
                  setSelectedPlanId("");
                }
              }}
              style={{
                fontSize: "12.5px",
                padding: "6px 12px",
                borderRadius: "8px",
                border: "1px solid #86efac",
                background: "#ffffff",
                color: "#1e293b",
                fontWeight: 600,
              }}
            >
              <option value="">Standard 1-Acre Template</option>
              {plans.map((p) => (
                <option key={p.plan_id} value={p.plan_id}>
                  {p.crop} ({p.district} · {p.land_size_acres} Acres · {formatDate(p.planting_date)})
                </option>
              ))}
            </select>
          </div>

          <span style={{ fontSize: "11.5px", color: "#15803d" }}>
            Viewing agronomic schedule and inputs based on approved DOA practices.
          </span>
        </div>
      )}

      {/* TOP CARD */}
      <div
        style={{
          background: "#ffffff",
          borderRadius: "22px",
          border: "1px solid #e2e8f0",
          boxShadow: "0 4px 16px rgba(0, 0, 0, 0.03)",
          padding: "24px",
          marginBottom: "24px",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "auto 1fr auto",
            gap: "24px",
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <div
            style={{
              width: "120px",
              height: "120px",
              borderRadius: "18px",
              overflow: "hidden",
              position: "relative",
              boxShadow: "0 4px 10px rgba(0,0,0,0.06)",
              flexShrink: 0,
            }}
          >
            <Image
              src={CROPS_LIST.find((c) => c.name === selectedCrop)?.image || "/images/crop_okra_detail.jpg"}
              alt={selectedCrop}
              fill
              style={{ objectFit: "cover" }}
              priority
            />
          </div>

          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap", marginBottom: "8px" }}>
              <h2 style={{ fontSize: "24px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                {activeCropData.commonName}
              </h2>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "5px",
                  padding: "4px 10px",
                  borderRadius: "8px",
                  fontSize: "12px",
                  fontWeight: 700,
                  background: "#f0fdf4",
                  color: "#15803d",
                  border: "1px solid #bbf7d0",
                }}
              >
                <ShieldCheck size={14} /> Approved DOA Guidance
              </span>
            </div>

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "18px",
                fontSize: "12.5px",
                color: "#64748b",
                marginTop: "10px",
              }}
            >
              <div>
                <span style={{ color: "#94a3b8", display: "block", fontSize: "11px" }}>Growing Method</span>
                <strong style={{ color: "#1e293b" }}>{activeCropData.method}</strong>
              </div>
              <div>
                <span style={{ color: "#94a3b8", display: "block", fontSize: "11px" }}>Plant Spacing</span>
                <strong style={{ color: "#1e293b" }}>{activeCropData.spacing}</strong>
              </div>
              <div>
                <span style={{ color: "#94a3b8", display: "block", fontSize: "11px" }}>Land Area</span>
                <strong style={{ color: "#1e293b" }}>{acres} Acre(s)</strong>
              </div>
              <div>
                <span style={{ color: "#94a3b8", display: "block", fontSize: "11px" }}>Growth Duration</span>
                <strong style={{ color: "#1e293b" }}>~{activeCropData.durationDays} Days</strong>
              </div>
              <div>
                <span style={{ color: "#94a3b8", display: "block", fontSize: "11px" }}>Applicable Seasons</span>
                <strong style={{ color: "#1e293b" }}>{activeCropData.season}</strong>
              </div>
            </div>
          </div>

          <div>
            <Link
              href="/crop-planning/plans"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "10px 16px",
                background: "#f8fafc",
                border: "1px solid #cbd5e1",
                borderRadius: "12px",
                fontSize: "13px",
                fontWeight: 600,
                color: "#1e293b",
                textDecoration: "none",
                whiteSpace: "nowrap",
              }}
            >
              Register a Plan <ChevronRight size={15} />
            </Link>
          </div>
        </div>

        <div
          style={{
            marginTop: "20px",
            background: "#fffbeb",
            borderRadius: "14px",
            border: "1px solid #fef3c7",
            padding: "14px 18px",
            display: "flex",
            alignItems: "flex-start",
            gap: "12px",
          }}
        >
          <Lightbulb size={20} style={{ color: "#d97706", flexShrink: 0, marginTop: "2px" }} />
          <div>
            <strong style={{ fontSize: "13px", color: "#92400e", display: "block" }}>Agronomic Guidance</strong>
            <p style={{ fontSize: "12.5px", color: "#b45309", margin: "2px 0 0 0", lineHeight: 1.45 }}>
              The cultivation method below follows standard research-backed guidance from the Sri Lanka Department of Agriculture (DOA) for <strong>{activeCropData.commonName}</strong>.
            </p>
          </div>
        </div>

        {/* Stepper Bar */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(6, 1fr)",
            gap: "10px",
            marginTop: "24px",
            paddingTop: "20px",
            borderTop: "1px solid #f1f5f9",
          }}
        >
          {[
            { step: 1, label: "Crop Selection", done: true },
            { step: 2, label: "Land Preparation", id: "land-prep" },
            { step: 3, label: "Planting", id: "planting" },
            { step: 4, label: "Crop Management", id: "vegetative" },
            { step: 5, label: "Harvesting", id: "harvesting" },
            { step: 6, label: "Post-Harvest", done: false },
          ].map((s) => {
            const isSelected = s.id === selectedStageId;
            return (
              <button
                key={s.step}
                onClick={() => s.id && setSelectedStageId(s.id)}
                style={{
                  background: isSelected ? "#f0fdf4" : "transparent",
                  border: isSelected ? "1px solid #86efac" : "1px solid transparent",
                  borderRadius: "10px",
                  padding: "6px 8px",
                  cursor: s.id ? "pointer" : "default",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  textAlign: "left",
                }}
              >
                <div
                  style={{
                    width: "22px",
                    height: "22px",
                    borderRadius: "50%",
                    background: s.done ? "#16a34a" : isSelected ? "#15803d" : "#e2e8f0",
                    color: s.done || isSelected ? "#ffffff" : "#64748b",
                    fontSize: "11px",
                    fontWeight: 700,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  {s.done ? <Check size={13} /> : s.step}
                </div>
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: isSelected ? 700 : 500,
                    color: isSelected ? "#15803d" : "#475569",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {s.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* MIDDLE SECTION */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gap: "24px",
          marginBottom: "24px",
        }}
      >
        {/* Timeline */}
        <div
          style={{
            background: "#ffffff",
            borderRadius: "22px",
            border: "1px solid #e2e8f0",
            padding: "24px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.02)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
            <div>
              <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                Growth Timeline & Stages
              </h3>
              <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>
                Key activities from land preparation to harvest.
              </p>
            </div>

            <div style={{ display: "flex", background: "#f1f5f9", borderRadius: "10px", padding: "3px" }}>
              <button
                onClick={() => setTimelineView("timeline")}
                style={{
                  border: "none",
                  padding: "5px 12px",
                  borderRadius: "8px",
                  fontSize: "11.5px",
                  fontWeight: 600,
                  background: timelineView === "timeline" ? "#15803d" : "transparent",
                  color: timelineView === "timeline" ? "#ffffff" : "#64748b",
                  cursor: "pointer",
                }}
              >
                Timeline View
              </button>
              <button
                onClick={() => setTimelineView("calendar")}
                style={{
                  border: "none",
                  padding: "5px 12px",
                  borderRadius: "8px",
                  fontSize: "11.5px",
                  fontWeight: 600,
                  background: timelineView === "calendar" ? "#15803d" : "transparent",
                  color: timelineView === "calendar" ? "#ffffff" : "#64748b",
                  cursor: "pointer",
                }}
              >
                Calendar View
              </button>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: `repeat(${dynamicStages.length}, 1fr)`,
              gap: "8px",
              overflowX: "auto",
              paddingBottom: "8px",
            }}
          >
            {dynamicStages.map((stage, idx) => {
              const isSelected = stage.id === selectedStageId;
              return (
                <div
                  key={stage.id}
                  onClick={() => setSelectedStageId(stage.id)}
                  style={{
                    cursor: "pointer",
                    textAlign: "center",
                    padding: "12px 6px",
                    borderRadius: "14px",
                    background: isSelected ? "#f0fdf4" : "#fafafa",
                    border: isSelected ? "1.5px solid #16a34a" : "1px solid #f1f5f9",
                    transition: "all 0.2s",
                  }}
                >
                  <div
                    style={{
                      width: "44px",
                      height: "44px",
                      borderRadius: "50%",
                      margin: "0 auto 8px auto",
                      background: isSelected ? "#dcfce7" : "#e2e8f0",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: isSelected ? "#15803d" : "#64748b",
                    }}
                  >
                    <Sprout size={idx === 0 ? 18 : idx === 1 ? 20 : idx === 2 ? 22 : idx === 3 ? 24 : 26} />
                  </div>

                  <strong style={{ fontSize: "12px", color: isSelected ? "#14532d" : "#1e293b", display: "block" }}>
                    {stage.title}
                  </strong>
                  <span style={{ fontSize: "10px", color: "#64748b", display: "block", marginTop: "3px" }}>
                    {stage.formattedRange}
                  </span>

                  <span
                    style={{
                      display: "inline-block",
                      marginTop: "6px",
                      fontSize: "9.5px",
                      fontWeight: 700,
                      padding: "2px 6px",
                      borderRadius: "6px",
                      background:
                        stage.status === "Completed"
                          ? "#dcfce7"
                          : stage.status === "Current Stage"
                          ? "#dbeafe"
                          : "#f1f5f9",
                      color:
                        stage.status === "Completed"
                          ? "#15803d"
                          : stage.status === "Current Stage"
                          ? "#1d4ed8"
                          : "#64748b",
                    }}
                  >
                    {stage.status}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Seasonal Overview */}
        <div
          style={{
            background: "#ffffff",
            borderRadius: "22px",
            border: "1px solid #e2e8f0",
            padding: "24px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.02)",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <Leaf size={18} style={{ color: "#16a34a" }} />
              <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                Seasonal Overview
              </h3>
            </div>
            <p style={{ fontSize: "12px", color: "#64748b", margin: "0 0 16px 0" }}>
              Growing parameters for {activeCropData.commonName}.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "12px", border: "1px solid #f1f5f9" }}>
                <span style={{ fontSize: "11px", color: "#64748b", display: "flex", alignItems: "center", gap: "5px" }}>
                  <Clock size={12} /> Total Duration
                </span>
                <strong style={{ fontSize: "16px", color: "#0f172a", display: "block", marginTop: "4px" }}>
                  {activeCropData.durationDays} days
                </strong>
              </div>

              <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "12px", border: "1px solid #f1f5f9" }}>
                <span style={{ fontSize: "11px", color: "#64748b", display: "flex", alignItems: "center", gap: "5px" }}>
                  <Calendar size={12} /> Target Planting
                </span>
                <strong style={{ fontSize: "14px", color: "#0f172a", display: "block", marginTop: "4px" }}>
                  {formatShortDate(plantingDate)}
                </strong>
              </div>

              <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "12px", border: "1px solid #f1f5f9" }}>
                <span style={{ fontSize: "11px", color: "#64748b", display: "flex", alignItems: "center", gap: "5px" }}>
                  <CalendarDays size={12} /> Target Harvest
                </span>
                <strong style={{ fontSize: "14px", color: "#0f172a", display: "block", marginTop: "4px" }}>
                  {formatShortDate(addDays(plantingDate, activeCropData.durationDays))}
                </strong>
              </div>

              <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "12px", border: "1px solid #f1f5f9" }}>
                <span style={{ fontSize: "11px", color: "#64748b", display: "flex", alignItems: "center", gap: "5px" }}>
                  <Sprout size={12} /> Method
                </span>
                <strong style={{ fontSize: "13.5px", color: "#0f172a", display: "block", marginTop: "4px" }}>
                  {activeCropData.method}
                </strong>
              </div>
            </div>
          </div>

          <div style={{ marginTop: "16px", fontSize: "11px", color: "#94a3b8", borderTop: "1px solid #f1f5f9", paddingTop: "12px" }}>
            Guidelines verified from Sri Lanka Department of Agriculture (DOA).
          </div>
        </div>
      </div>

      {/* BOTTOM SECTION */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gap: "24px",
        }}
      >
        {/* Detailed Activities */}
        <div
          style={{
            background: "#ffffff",
            borderRadius: "22px",
            border: "1px solid #e2e8f0",
            padding: "24px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.02)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "18px" }}>
            <div>
              <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                Detailed Activities
              </h3>
              <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>
                Follow these recommended agronomic practices for each stage.
              </p>
            </div>

            <button
              onClick={() => window.print()}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "8px 14px",
                background: "#f8fafc",
                border: "1px solid #cbd5e1",
                borderRadius: "10px",
                fontSize: "12px",
                fontWeight: 600,
                color: "#1e293b",
                cursor: "pointer",
              }}
            >
              <Download size={14} /> Download Guide (PDF)
            </button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "190px 1fr", gap: "20px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {dynamicStages.map((st) => {
                const active = st.id === selectedStageId;
                return (
                  <button
                    key={st.id}
                    onClick={() => setSelectedStageId(st.id)}
                    style={{
                      textAlign: "left",
                      padding: "10px 12px",
                      borderRadius: "12px",
                      background: active ? "#f0fdf4" : "transparent",
                      border: active ? "1px solid #86efac" : "1px solid transparent",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <div>
                      <strong style={{ fontSize: "12.5px", color: active ? "#14532d" : "#334155", display: "block" }}>
                        {st.title}
                      </strong>
                      <span style={{ fontSize: "10.5px", color: "#94a3b8" }}>{st.formattedRange}</span>
                    </div>
                    {active && <ChevronRight size={14} style={{ color: "#16a34a" }} />}
                  </button>
                );
              })}
            </div>

            <div style={{ background: "#f8fafc", borderRadius: "16px", padding: "18px", border: "1px solid #f1f5f9" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
                <div>
                  <h4 style={{ fontSize: "16px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                    {activeStage.title}
                  </h4>
                  <span style={{ fontSize: "11.5px", color: "#64748b" }}>{activeStage.formattedRange}</span>
                </div>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    padding: "3px 8px",
                    borderRadius: "6px",
                    background: "#dcfce7",
                    color: "#15803d",
                  }}
                >
                  {activeStage.status}
                </span>
              </div>

              <div
                style={{
                  height: "150px",
                  borderRadius: "12px",
                  overflow: "hidden",
                  position: "relative",
                  marginBottom: "16px",
                }}
              >
                <Image src={activeStage.image} alt={activeStage.title} fill style={{ objectFit: "cover" }} />
              </div>

              <strong style={{ fontSize: "13px", color: "#0f172a", display: "block", marginBottom: "8px" }}>
                Key Guidance
              </strong>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "16px" }}>
                {activeStage.guidance.map((item, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "8px", fontSize: "12.5px", color: "#334155" }}>
                    <CheckCircle2 size={15} style={{ color: "#16a34a", flexShrink: 0, marginTop: "2px" }} />
                    <span>{item}</span>
                  </div>
                ))}
              </div>

              <div style={{ background: "#fffbeb", borderRadius: "10px", padding: "10px 12px", border: "1px solid #fef3c7" }}>
                <span style={{ fontSize: "11.5px", fontWeight: 700, color: "#92400e", display: "block" }}>
                  Important Notes
                </span>
                <p style={{ fontSize: "11.5px", color: "#b45309", margin: "2px 0 0 0" }}>{activeStage.notes}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Inputs & GAP */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div
            style={{
              background: "#ffffff",
              borderRadius: "22px",
              border: "1px solid #e2e8f0",
              padding: "22px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.02)",
            }}
          >
            <h4 style={{ fontSize: "15px", fontWeight: 800, color: "#0f172a", margin: "0 0 4px 0" }}>
              Input Requirements (Indicative)
            </h4>
            <p style={{ fontSize: "11.5px", color: "#64748b", margin: "0 0 16px 0" }}>
              Calculated for <strong>{acres} acre(s)</strong> of land.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "12.5px", borderBottom: "1px solid #f1f5f9", paddingBottom: "8px" }}>
                <span style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "6px" }}>
                  <Leaf size={14} style={{ color: "#16a34a" }} /> Organic manure
                </span>
                <strong style={{ color: "#0f172a" }}>{(req.manureTonsPerAcre * acres).toFixed(1)} tons</strong>
              </div>

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "12.5px", borderBottom: "1px solid #f1f5f9", paddingBottom: "8px" }}>
                <span style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "6px" }}>
                  <Sprout size={14} style={{ color: "#d97706" }} /> Basal Urea
                </span>
                <strong style={{ color: "#0f172a" }}>{(req.basalUreaKg * acres).toFixed(0)} kg</strong>
              </div>

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "12.5px", borderBottom: "1px solid #f1f5f9", paddingBottom: "8px" }}>
                <span style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "6px" }}>
                  <Sprout size={14} style={{ color: "#d97706" }} /> Basal TSP / Phosphate
                </span>
                <strong style={{ color: "#0f172a" }}>{(req.basalTspKg * acres).toFixed(0)} kg</strong>
              </div>

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "12.5px", borderBottom: "1px solid #f1f5f9", paddingBottom: "8px" }}>
                <span style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "6px" }}>
                  <Sprout size={14} style={{ color: "#d97706" }} /> Basal MOP / Potassium
                </span>
                <strong style={{ color: "#0f172a" }}>{(req.basalMopKg * acres).toFixed(0)} kg</strong>
              </div>

              {req.topDressingUreaKg > 0 && (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "12.5px", borderBottom: "1px solid #f1f5f9", paddingBottom: "8px" }}>
                  <span style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "6px" }}>
                    <Sprout size={14} style={{ color: "#2563eb" }} /> Top Dressing Urea
                  </span>
                  <strong style={{ color: "#0f172a" }}>{(req.topDressingUreaKg * acres).toFixed(0)} kg</strong>
                </div>
              )}

              <div style={{ fontSize: "12px", color: "#64748b", paddingTop: "4px" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#2563eb", fontWeight: 600, marginBottom: "2px" }}>
                  <Droplets size={13} /> Irrigation requirement
                </span>
                <span>{req.irrigationNote}</span>
              </div>
            </div>
          </div>

          <div
            style={{
              background: "#ffffff",
              borderRadius: "22px",
              border: "1px solid #e2e8f0",
              padding: "22px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.02)",
            }}
          >
            <h4 style={{ fontSize: "15px", fontWeight: 800, color: "#0f172a", margin: "0 0 12px 0" }}>
              Good Agricultural Practices
            </h4>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px", color: "#334155" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Check size={14} style={{ color: "#16a34a" }} />
                <span>Use certified high-viability seeds or seedlings.</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Check size={14} style={{ color: "#16a34a" }} />
                <span>Follow Integrated Pest Management (IPM).</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Check size={14} style={{ color: "#16a34a" }} />
                <span>Maintain regular irrigation and avoid waterlogging.</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Check size={14} style={{ color: "#16a34a" }} />
                <span>Keep the plot weed-free during early growth.</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Check size={14} style={{ color: "#16a34a" }} />
                <span>Harvest at recommended maturity for peak market value.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
