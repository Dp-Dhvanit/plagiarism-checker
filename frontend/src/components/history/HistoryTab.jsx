import { useCallback, useEffect, useState } from "react";
import PageHeader from "../common/PageHeader.jsx";
import GlassCard from "../common/GlassCard.jsx";
import Icon from "../common/Icon.jsx";
import Button from "../common/Button.jsx";
import ErrorMsg from "../common/ErrorMsg.jsx";
import EmptyState from "../common/EmptyState.jsx";
import HistoryItem from "./HistoryItem.jsx";
import HistoryDetailPanel from "./HistoryDetailPanel.jsx";
import { deleteJSON, downloadFile, getJSON } from "../../lib/api.js";

const FILTERS = [
  { key: "all", label: "All", icon: "apps" },
  { key: "text", label: "Text", icon: "description" },
  { key: "image", label: "Image", icon: "image" },
];

/** The record id in a "#history/12" deep link, or null. */
function historyIdFromHash() {
  const [surface, id] = window.location.hash.replace("#", "").split("/");
  const n = Number(id);
  return surface === "history" && Number.isInteger(n) && n > 0 ? n : null;
}

export default function HistoryTab({ onNavigate }) {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("newest");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState(null);
  const [confirmId, setConfirmId] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setItems(await getJSON(`/history?filter=${filter}&sort=${sort}`));
    } catch (e) {
      setError(e.message || "Could not load the analysis history.");
    } finally {
      setLoading(false);
    }
  }, [filter, sort]);

  useEffect(() => { load(); }, [load]);

  // Open the record named in the URL (#history/12) — on arrival, and again if the
  // hash changes while this tab is open. A record that no longer exists (deleted
  // since the link was made) reports that instead of showing a blank page.
  useEffect(() => {
    let cancelled = false;
    const openFromHash = async () => {
      const id = historyIdFromHash();
      if (!id) return;
      try {
        const d = await getJSON(`/history/${id}`);
        if (!cancelled) setDetail(d);
      } catch {
        if (!cancelled) setError("That analysis is no longer on record — it may have been deleted.");
      }
    };
    openFromHash();
    window.addEventListener("hashchange", openFromHash);
    return () => {
      cancelled = true;
      window.removeEventListener("hashchange", openFromHash);
    };
  }, []);

  const closeDetail = () => {
    setDetail(null);
    if (historyIdFromHash()) window.history.replaceState(null, "", "#history");
  };

  const view = async (id) => {
    setBusyId(id);
    setError("");
    try {
      setDetail(await getJSON(`/history/${id}`));
    } catch (e) {
      setError(e.message || "Could not open this analysis.");
    } finally {
      setBusyId(null);
    }
  };

  const download = async (id) => {
    setBusyId(id);
    setError("");
    try {
      await downloadFile(`/report/${id}`, `analysis_${id}_report.pdf`);
    } catch (e) {
      setError(e.message || "Could not generate the report.");
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (id) => {
    setBusyId(id);
    setError("");
    try {
      await deleteJSON(`/history/${id}`);
      setConfirmId(null);
      await load();
    } catch (e) {
      setError(e.message || "Could not delete this analysis.");
    } finally {
      setBusyId(null);
    }
  };

  if (detail) {
    return <HistoryDetailPanel detail={detail} onClose={closeDetail} />;
  }

  return (
    <>
      <PageHeader
        title="History"
        subtitle="Every analysis this terminal has run, newest first."
        status={items.length ? "done" : "idle"}
        statusLabel={loading ? "Loading" : `${items.length} record${items.length === 1 ? "" : "s"}`}
        action={
          <Button onClick={load} variant="ghost" size="sm" icon="refresh" loading={loading}>
            Refresh
          </Button>
        }
      />

      <GlassCard bodyClassName="p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex gap-1 rounded-lg bg-surface-lowest p-1">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setFilter(f.key)}
                className={`flex items-center gap-2 rounded-md px-3.5 py-2 text-[13px] font-medium transition-colors ${
                  filter === f.key
                    ? "bg-surface text-primary shadow-soft"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                <Icon name={f.icon} size={16} />
                {f.label}
              </button>
            ))}
          </div>

          <label className="flex items-center gap-2.5">
            <span className="text-[12.5px] font-medium text-on-surface-variant">Sort</span>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="field rounded-lg px-3 py-2 text-[13px] outline-none"
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
          </label>
        </div>
      </GlassCard>

      <ErrorMsg msg={error} />

      <div className="mt-6">
        {loading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-[84px] animate-pulse rounded-xl border border-outline-variant/30 bg-surface-low" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <GlassCard bodyClassName="p-0">
            <EmptyState
              icon="history"
              title="No analyses recorded yet"
              message="Run a text, document or image analysis and it will be archived here with its scores and PDF report."
              action={
                <div className="flex flex-wrap justify-center gap-3">
                  <Button onClick={() => onNavigate?.("text")} icon="description">Analyze text</Button>
                  <Button onClick={() => onNavigate?.("file")} variant="ghost" icon="upload_file">Upload a document</Button>
                </div>
              }
            />
          </GlassCard>
        ) : (
          <ul className="space-y-3">
            {items.map((item) => (
              <HistoryItem
                key={item.id}
                item={item}
                busy={busyId === item.id}
                confirming={confirmId === item.id}
                onView={() => view(item.id)}
                onDownload={() => download(item.id)}
                onRequestDelete={() => setConfirmId(item.id)}
                onConfirmDelete={() => remove(item.id)}
                onCancelDelete={() => setConfirmId(null)}
              />
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
