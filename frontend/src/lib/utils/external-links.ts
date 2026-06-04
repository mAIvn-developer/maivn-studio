// MARK: Constants

const DEFAULT_MARKETING_SITE_ORIGIN = "https://maivn.io";
const DEFAULT_DEVELOPER_PORTAL_ORIGIN = "https://developer.maivn.io";

// MARK: Helpers

function readPublicEnv(name: string): string | undefined {
  const env = (import.meta as { env?: Record<string, string | undefined> }).env;
  return env?.[name];
}

function normalizeOrigin(value: string): string {
  const withProtocol = /^https?:\/\//i.test(value) ? value : `https://${value}`;
  return withProtocol.replace(/\/$/, "");
}

function joinUrl(origin: string, path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${origin}${normalizedPath}`;
}

// MARK: Public API

function getMarketingSiteOrigin(): string {
  const configured = readPublicEnv("PUBLIC_MARKETING_SITE_URL");
  if (configured && configured.trim().length > 0) {
    return normalizeOrigin(configured.trim());
  }
  return DEFAULT_MARKETING_SITE_ORIGIN;
}

function getDeveloperPortalOrigin(): string {
  const configured = readPublicEnv("PUBLIC_DEVELOPER_PORTAL_URL");
  if (configured && configured.trim().length > 0) {
    return normalizeOrigin(configured.trim());
  }
  return DEFAULT_DEVELOPER_PORTAL_ORIGIN;
}

export const externalLinks = {
  marketingSite: () => getMarketingSiteOrigin(),
  developerPortal: () => getDeveloperPortalOrigin(),
  developerPortalDocs: () => joinUrl(getDeveloperPortalOrigin(), "/docs"),
  developerPortalWaitlist: () => joinUrl(getDeveloperPortalOrigin(), "/waitlist"),
  contact: () => "mailto:hello@maivn.io",
};
