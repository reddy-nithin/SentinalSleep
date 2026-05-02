import { getRecentInterventions } from "@/lib/data";
import { InterventionsClient } from "./InterventionsClient";

export default function InterventionsPage() {
  const interventions = getRecentInterventions();
  return <InterventionsClient interventions={interventions} />;
}
