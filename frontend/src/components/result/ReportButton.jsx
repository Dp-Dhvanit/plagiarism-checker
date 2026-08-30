import { useState } from "react";
import Button from "../common/Button.jsx";
import ErrorMsg from "../common/ErrorMsg.jsx";
import { downloadFile } from "../../lib/api.js";

/** Generates the existing server-side PDF report for a stored analysis. */
export default function ReportButton({ historyId, label = "Generate PDF report", variant = "ghost", full = false }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const download = async () => {
    setBusy(true);
    setError("");
    try {
      await downloadFile(`/report/${historyId}`, `analysis_${historyId}_report.pdf`);
    } catch (e) {
      setError(e.message || "Could not generate the report.");
    } finally {
      setBusy(false);
    }
  };

  if (historyId == null) return null;

  return (
    <div className={full ? "w-full" : ""}>
      <Button onClick={download} loading={busy} variant={variant} icon="picture_as_pdf" full={full}>
        {busy ? "Generating…" : label}
      </Button>
      <ErrorMsg msg={error} />
    </div>
  );
}
