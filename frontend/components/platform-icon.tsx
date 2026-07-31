import { Globe, Layers, Monitor, Smartphone, Webhook } from "lucide-react";
import type { Platform } from "@/lib/types";

const ICONS: Record<Platform, React.ComponentType<{ className?: string }>> = {
  web: Globe,
  rest_api: Webhook,
  graphql: Layers,
  mobile: Smartphone,
  desktop: Monitor,
};

export const PLATFORM_LABELS: Record<Platform, string> = {
  web: "Web",
  rest_api: "REST API",
  graphql: "GraphQL",
  mobile: "Mobile",
  desktop: "Desktop",
};

export function PlatformIcon({ platform, className }: { platform: Platform; className?: string }) {
  const Icon = ICONS[platform] ?? Globe;
  return <Icon className={className} />;
}
