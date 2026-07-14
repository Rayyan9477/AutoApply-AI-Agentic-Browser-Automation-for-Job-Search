/** Status + score presentation, mapped to the design's token palette. Shared by the
 *  pipeline table, status pills, and the app-detail drawer. */

export interface StatusMeta {
  label: string;
  color: string;
  soft: string;
}

const DEFAULT_STATUS: StatusMeta = { label: 'Queued', color: 'var(--q)', soft: 'var(--q-soft)' };

const STATUS: Record<string, StatusMeta> = {
  queued: DEFAULT_STATUS,
  pending_review: { label: 'Needs review', color: 'var(--review)', soft: 'var(--review-soft)' },
  approved: { label: 'Approved', color: 'var(--approved)', soft: 'var(--approved-soft)' },
  applying: { label: 'Applying', color: 'var(--accent)', soft: 'var(--accent-soft)' },
  applied: { label: 'Applied', color: 'var(--applied)', soft: 'var(--applied-soft)' },
  interview: { label: 'Interview', color: 'var(--interview)', soft: 'var(--interview-soft)' },
  offer: { label: 'Offer', color: 'var(--offer)', soft: 'var(--offer-soft)' },
  rejected: { label: 'Rejected', color: 'var(--rejected)', soft: 'var(--rejected-soft)' },
  withdrawn: { label: 'Withdrawn', color: 'var(--withdrawn)', soft: 'var(--q-soft)' },
  failed: { label: 'Failed', color: 'var(--failed)', soft: 'var(--failed-soft)' },
};

export function statusMeta(status: string): StatusMeta {
  return STATUS[status] ?? DEFAULT_STATUS;
}

/** A status is actionable (can be approved) when queued or awaiting review. */
export function isApprovable(status: string): boolean {
  return status === 'pending_review' || status === 'queued';
}

/**
 * Scale a 0–1 ATS/match score (as the API returns it) to a 0–100 integer for display.
 * Use this everywhere a score is shown or passed to {@link atsColor} — the raw 0–1 value
 * would otherwise render as "0"/"1" and always land in the rejected color band.
 */
export function atsPercent(score: number | null | undefined): number {
  return Math.round((score ?? 0) * 100);
}

/** ATS-score color band (offer / applied / review / rejected). Expects a 0–100 value. */
export function atsColor(score: number): string {
  if (score >= 85) return 'var(--offer)';
  if (score >= 75) return 'var(--applied)';
  if (score >= 65) return 'var(--review)';
  return 'var(--rejected)';
}

/** Compact relative time ("just now", "5m", "3h", "2d", or a short date). */
export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '—';
  const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (secs < 60) return 'just now';
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
