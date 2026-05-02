import { getNightData } from "@/lib/data";
import { NightDetailClient } from "./NightDetailClient";

interface Props {
  params: Promise<{ sessionId: string }>;
}

export default async function NightDetailPage({ params }: Props) {
  const { sessionId } = await params;
  const data = getNightData(sessionId);
  return <NightDetailClient data={data} />;
}
