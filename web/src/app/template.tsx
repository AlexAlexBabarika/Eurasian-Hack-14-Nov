import { TourDock } from "@/components/tour/TourDock";

// Mounts the judge tour on every page without touching the pages themselves.
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <TourDock />
    </>
  );
}
