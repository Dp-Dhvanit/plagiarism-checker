import { useEffect, useState } from "react";
import PageHeader from "../common/PageHeader.jsx";
import ErrorMsg from "../common/ErrorMsg.jsx";
import StatTile from "../common/StatTile.jsx";
import { getJSON } from "../../lib/api.js";
import { TERMINAL_NAME } from "../../data/constants.js";

/**
 * The landing surface after boot. This IS the overview: a bigger read on
 * the terminal's stats. It deliberately has no module launcher — the
 * sidebar already lists every module, so a second set of the same links
 * here was redundant and, per feedback, confusing.
 */
export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getJSON("/dashboard")
      .then((d) => !cancelled && setStats(d))
      .catch((e) => !cancelled && setError(e.message || "Could not load terminal statistics."));
    return () => { cancelled = true; };
  }, []);

  return (
    <>
      <PageHeader
        eyebrow="SEC_00 // OVERVIEW"
        title={TERMINAL_NAME}
        subtitle="Use the sidebar to open a module."
        status={stats ? "ready" : "idle"}
        statusLabel={stats ? "SYSTEM READY" : "SYNCING"}
      />

      <ErrorMsg msg={error} />

      {/* Terminal statistics — the page's main content. Codes name what
          each tile actually shows instead of an arbitrary MTR_01.. count. */}
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-5">
        {stats ? (
          <>
            <StatTile size="lg" code="RUNS" label="Total runs" icon="analytics" value={stats.total_analyses} hex="#b4c5ff" />
            <StatTile size="lg" code="TEXT" label="Text" icon="description" value={stats.text_analyses} hex="#e5e1e4" />
            <StatTile size="lg" code="IMAGE" label="Image" icon="image" value={stats.image_analyses} hex="#e5e1e4" />
            <StatTile size="lg" code="FLAGGED" label="AI flagged" icon="flag" value={stats.ai_flagged} hex="#ddb8ff" />
            <StatTile
              size="lg"
              code="SIMILARITY"
              label="Avg similarity"
              icon="compare_arrows"
              value={`${stats.average_similarity}%`}
              hex="#b3d17a"
            />
          </>
        ) : (
          [0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-[168px] animate-pulse rounded-lg border border-outline-variant/20 bg-surface-low/30"
            />
          ))
        )}
      </div>
    </>
  );
}
