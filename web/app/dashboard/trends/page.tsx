import { getTrends } from "@/lib/data";
import { TrendsClient } from "./TrendsClient";

export default function TrendsPage() {
  const t = getTrends();
  return <TrendsClient t={t} />;
}
