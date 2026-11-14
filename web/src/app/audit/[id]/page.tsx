import { AuditView } from "@/components/AuditView";

export default async function AuditPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ before?: string | string[] }>;
}) {
  const [{ id }, { before }] = await Promise.all([params, searchParams]);
  return <AuditView id={decodeURIComponent(id)} before={Array.isArray(before) ? before[0] : before} />;
}
