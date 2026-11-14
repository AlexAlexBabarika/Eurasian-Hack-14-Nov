import { dataCategoryLabel, humanize } from "@/lib/labels";
import type { Jurisdiction, Observation } from "@/lib/types";

export const ROW_GAP = 8;
export const CATEGORY_HEIGHT = 32;
export const VENDOR_HEIGHT = 56;
export const COUNTRY_HEIGHT = 56;

const EEA =
  "AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE IS LI NO".split(" ");
const HOME: Record<Jurisdiction, string[]> = { UK: ["GB", "UK"], EU: EEA, KZ: ["KZ"] };
const UNKNOWN = "unknown";

export type FlowCategory = { key: string; label: string; y: number };
export type FlowVendor = {
  key: string;
  name: string;
  purpose: string;
  isAi: boolean;
  preConsent: boolean;
  named: boolean;
  categories: string[];
  country: string;
  y: number;
};
export type FlowCountry = { key: string; name: string; known: boolean; crossBorder: Jurisdiction[]; vendors: number; y: number };
export type FlowLink = { vendor: string; category?: string; y1: number; y2: number };
export type Flow = {
  categories: FlowCategory[];
  vendors: FlowVendor[];
  countries: FlowCountry[];
  categoryLinks: FlowLink[];
  countryLinks: FlowLink[];
  height: number;
};

export function isNamedInPolicy(vendor: string, namedProcessors: string[]): boolean {
  const name = vendor.trim().toLowerCase();
  return namedProcessors.some((item) => {
    const named = item.trim().toLowerCase();
    return named.length > 0 && (name === named || name.startsWith(`${named} `));
  });
}

export function countryName(code: string): string {
  if (code === UNKNOWN) return "Unknown location";
  try {
    return new Intl.DisplayNames(["en"], { type: "region" }).of(code === "UK" ? "GB" : code) ?? code;
  } catch {
    return code;
  }
}

function span(count: number, rowHeight: number): number {
  return count * rowHeight + Math.max(count - 1, 0) * ROW_GAP;
}

function centres(count: number, rowHeight: number, total: number): number[] {
  const offset = (total - span(count, rowHeight)) / 2;
  return Array.from({ length: count }, (_, i) => offset + i * (rowHeight + ROW_GAP) + rowHeight / 2);
}

export function buildFlow(observations: Observation[], namedProcessors: string[], jurisdictions: Jurisdiction[]): Flow {
  const merged = new Map<string, Omit<FlowVendor, "y">>();
  for (const observation of observations) {
    if (!observation.vendor) continue;
    const key = observation.vendor.trim().toLowerCase();
    const country = observation.vendor_country?.trim().toUpperCase() || UNKNOWN;
    const existing = merged.get(key);
    if (existing) {
      existing.isAi ||= observation.is_ai;
      existing.preConsent ||= observation.pre_consent;
      existing.purpose ||= observation.purpose_guess ? humanize(observation.purpose_guess) : "";
      if (existing.country === UNKNOWN) existing.country = country;
      for (const category of observation.data_categories) {
        if (!existing.categories.includes(category)) existing.categories.push(category);
      }
    } else {
      merged.set(key, {
        key,
        name: observation.vendor,
        purpose: observation.purpose_guess ? humanize(observation.purpose_guess) : "",
        isAi: observation.is_ai,
        preConsent: observation.pre_consent,
        named: isNamedInPolicy(observation.vendor, namedProcessors),
        categories: [...observation.data_categories],
        country,
      });
    }
  }

  const countryKeys = [...new Set([...merged.values()].map((vendor) => vendor.country))].sort(
    (a, b) => Number(a === UNKNOWN) - Number(b === UNKNOWN),
  );
  // Vendors are grouped by country so the right-hand links do not cross.
  const vendorList = [...merged.values()].sort((a, b) => countryKeys.indexOf(a.country) - countryKeys.indexOf(b.country));
  const categoryKeys = [...new Set(vendorList.flatMap((vendor) => vendor.categories))];

  const height = Math.max(
    span(categoryKeys.length, CATEGORY_HEIGHT),
    span(vendorList.length, VENDOR_HEIGHT),
    span(countryKeys.length, COUNTRY_HEIGHT),
  );
  const categoryY = centres(categoryKeys.length, CATEGORY_HEIGHT, height);
  const vendorY = centres(vendorList.length, VENDOR_HEIGHT, height);
  const countryY = centres(countryKeys.length, COUNTRY_HEIGHT, height);

  const vendors = vendorList.map((vendor, i) => ({ ...vendor, y: vendorY[i] }));
  return {
    categories: categoryKeys.map((key, i) => ({ key, label: dataCategoryLabel(key), y: categoryY[i] })),
    vendors,
    countries: countryKeys.map((key, i) => ({
      key,
      name: countryName(key),
      known: key !== UNKNOWN,
      crossBorder: key === UNKNOWN ? [] : jurisdictions.filter((jurisdiction) => !HOME[jurisdiction].includes(key)),
      vendors: vendors.filter((vendor) => vendor.country === key).length,
      y: countryY[i],
    })),
    categoryLinks: vendors.flatMap((vendor) =>
      vendor.categories.map((category) => ({
        vendor: vendor.key,
        category,
        y1: categoryY[categoryKeys.indexOf(category)],
        y2: vendor.y,
      })),
    ),
    countryLinks: vendors.map((vendor) => ({ vendor: vendor.key, y1: vendor.y, y2: countryY[countryKeys.indexOf(vendor.country)] })),
    height,
  };
}
