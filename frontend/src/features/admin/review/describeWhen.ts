/** A stored UTC time as "Oct 28, 6:04 PM" in the viewer's zone. */
export function describeWhen(iso: string | null): string {
  if (!iso) return "";
  // Stored as UTC without a zone marker.
  const when = new Date(
    iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`,
  );
  return when.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
