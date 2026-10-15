import Link from "next/link";
import HistoricalLab from "../../components/historical-lab";

export default function HistoricalResearchPage() {
  return <div className="cp-stack"><Link className="cp-back" href="/crop-planning/research-demo">← Back to Crop Advisor</Link><HistoricalLab /></div>;
}
