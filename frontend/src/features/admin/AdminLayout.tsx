import React, { useEffect, useRef } from "react";
import { Link, NavLink, Outlet, useLocation, useMatch } from "react-router-dom";
import {
  ArrowLeft,
  AudioLines,
  Copy,
  Fingerprint,
  HardDrive,
  LayoutDashboard,
  ListChecks,
  MessageSquareHeart,
  MessageSquareWarning,
  ShieldAlert,
  ShieldCheck,
  TriangleAlert,
  Users,
  Waves,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { AccountMenu } from "@/features/session";
import { useLyricsFeedback } from "@/hooks/api/useLyricsFeedback";
import { useLyricsReports } from "@/hooks/api/useLyricsReports";
import { useBatchJobs } from "./hooks/useBatchJobs";
import {
  countAuditIssues,
  useDuplicatesScan,
  useFailedSongs,
  useLibraryAudit,
  useMetadataAudit,
  useSongsByFingerprintStatus,
} from "./hooks/useAdminQueries";

interface AdminSection {
  /** Relative to /admin; "" is the overview at /admin itself. */
  path: string;
  label: string;
  icon: LucideIcon;
  /** Shown beside the label. undefined = nothing to show (not loaded, a
   * scan that hasn't run yet, or a section that doesn't count anything). */
  useCount: () => number | undefined;
}

interface AdminSectionGroup {
  /** null: no heading (the overview, above the groups). */
  label: string | null;
  sections: AdminSection[];
}

function useNoCount() {
  return undefined;
}

function useLyricsReportCount() {
  return useLyricsReports().data?.length;
}

/** Songs someone said were off, counting only the lyrics they show now. */
function useLyricsFeedbackCount() {
  return useLyricsFeedback().data?.filter((e) => e.wayOff + e.aBitOff > 0)
    .length;
}

function useAcoustIdCount() {
  const suggested = useSongsByFingerprintStatus("suggested").data;
  const ambiguous = useSongsByFingerprintStatus("ambiguous").data;
  const noMatch = useSongsByFingerprintStatus("no_match").data;
  const failed = useSongsByFingerprintStatus("failed").data;
  if (!suggested || !ambiguous || !noMatch || !failed) return undefined;
  return suggested.length + ambiguous.length + noMatch.length + failed.length;
}

function useMetadataCount() {
  return useMetadataAudit().data?.total_flagged;
}

function useFailedCount() {
  return useFailedSongs().data?.length;
}

function useDuplicatesCount() {
  return useDuplicatesScan().data?.total_clusters;
}

function useDiskCount() {
  const summary = useLibraryAudit().data?.summary;
  return summary && countAuditIssues(summary);
}

/** Runs queued or going; nothing while the jobs are idle. */
function useActiveJobCount() {
  const jobs = useBatchJobs().data?.jobs;
  const active = jobs?.filter((job) => job.activeRun).length;
  return active ? active : undefined;
}

const ADMIN_SECTION_GROUPS: AdminSectionGroup[] = [
  {
    label: null,
    sections: [
      {
        path: "",
        label: "Overview",
        icon: LayoutDashboard,
        useCount: useNoCount,
      },
    ],
  },
  {
    label: "To review",
    sections: [
      {
        path: "lyrics-reports",
        label: "Lyrics reports",
        icon: MessageSquareWarning,
        useCount: useLyricsReportCount,
      },
      {
        path: "lyrics-feedback",
        label: "Lyrics feedback",
        icon: MessageSquareHeart,
        useCount: useLyricsFeedbackCount,
      },
      {
        path: "acoustid",
        label: "AcoustID",
        icon: Fingerprint,
        useCount: useAcoustIdCount,
      },
      {
        path: "metadata",
        label: "Metadata",
        icon: ShieldAlert,
        useCount: useMetadataCount,
      },
      {
        path: "failed",
        label: "Failed songs",
        icon: TriangleAlert,
        useCount: useFailedCount,
      },
      {
        path: "duplicates",
        label: "Duplicates",
        icon: Copy,
        useCount: useDuplicatesCount,
      },
      {
        path: "disk",
        label: "Disk check",
        icon: HardDrive,
        useCount: useDiskCount,
      },
    ],
  },
  {
    label: "Library",
    sections: [
      {
        path: "jobs",
        label: "Background jobs",
        icon: ListChecks,
        useCount: useActiveJobCount,
      },
      {
        path: "compare",
        label: "Compare stems",
        icon: Waves,
        useCount: useNoCount,
      },
      {
        path: "compare-breaks",
        label: "Compare breaks",
        icon: AudioLines,
        useCount: useNoCount,
      },
    ],
  },
  {
    label: "People",
    sections: [
      { path: "users", label: "Users", icon: Users, useCount: useNoCount },
    ],
  },
];

const ALL_SECTIONS = ADMIN_SECTION_GROUPS.flatMap((group) => group.sections);

function sectionUrl(section: AdminSection): string {
  return section.path ? `/admin/${section.path}` : "/admin";
}

const SidebarLink: React.FC<{ section: AdminSection }> = ({ section }) => {
  // Each section supplies its own hook; the list is static, so the hook
  // order never changes between renders.
  const count = section.useCount();
  const Icon = section.icon;
  // Every section's URL starts with /admin, so the overview matches exactly.
  const isActive = useMatch({ path: sectionUrl(section), end: !section.path });
  const linkRef = useRef<HTMLAnchorElement>(null);

  // At phone width the sidebar is a scrolling row; keep the open section in
  // view. A no-op in the full-height sidebar.
  useEffect(() => {
    if (isActive) {
      linkRef.current?.scrollIntoView({ block: "nearest", inline: "center" });
    }
  }, [isActive]);

  return (
    <NavLink
      ref={linkRef}
      to={sectionUrl(section)}
      end={!section.path}
      className={({ isActive }) =>
        cn(
          "flex shrink-0 items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
          isActive
            ? "bg-primary/15 font-semibold text-primary"
            : "text-surface-foreground/80 hover:bg-surface-foreground/10 hover:text-surface-foreground",
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="truncate">{section.label}</span>
      {count !== undefined && (
        <span
          className={cn(
            "ml-auto rounded-full px-2 text-xs tabular-nums",
            count > 0
              ? "bg-primary/20 text-primary"
              : "text-surface-foreground/50",
          )}
        >
          {count}
        </span>
      )}
    </NavLink>
  );
};

/**
 * Admin's own full-width shell: a sidebar of sections, grouped, with the
 * selected section beside it. Admin is used full screen on a laptop or the
 * TV, so it doesn't sit inside the guest app's column and bottom nav. At
 * phone width the sidebar becomes a scrolling row across the top.
 */
const AdminLayout: React.FC = () => {
  const location = useLocation();
  const path = location.pathname.replace(/\/+$/, "");
  const current = ALL_SECTIONS.find((section) =>
    section.path
      ? path.startsWith(sectionUrl(section))
      : path === sectionUrl(section),
  );

  return (
    <div className="flex h-screen flex-col md:flex-row">
      <aside className="flex shrink-0 flex-col gap-3 border-b border-border/40 bg-surface p-3 text-surface-foreground md:w-60 md:gap-5 md:border-b-0 md:border-r md:p-4">
        <div className="flex items-center justify-between gap-2 md:flex-col md:items-start">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <span className="font-display text-lg">Admin</span>
          </div>
          <Link
            to="/"
            className="flex items-center gap-1.5 text-xs text-surface-foreground/70 hover:text-surface-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to songbook
          </Link>
        </div>

        <nav className="flex gap-1 overflow-x-auto md:flex-col md:gap-5 md:overflow-x-visible">
          {ADMIN_SECTION_GROUPS.map((group) => (
            <div
              key={group.label ?? "top"}
              className="flex gap-1 md:flex-col md:gap-0.5"
            >
              {group.label && (
                <p className="hidden px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-surface-foreground/50 md:block">
                  {group.label}
                </p>
              )}
              {group.sections.map((section) => (
                <SidebarLink key={section.path} section={section} />
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <main className="relative min-w-0 flex-1 overflow-auto p-4 md:p-8">
        <AccountMenu className="lg:absolute lg:top-2 lg:right-3 lg:z-30" />
        {current && (
          <h1 className="mb-6 text-2xl font-bold">{current.label}</h1>
        )}
        <Outlet />
      </main>
    </div>
  );
};

export default AdminLayout;
