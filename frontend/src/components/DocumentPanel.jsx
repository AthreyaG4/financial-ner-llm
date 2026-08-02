import Spinner from "./Spinner.jsx";

export default function DocumentPanel({
  fileName,
  fileMeta,
  isParsed,
  isLoading,
  isResultsSuccess,
  entitiesCount,
  elapsedLabel,
  isErrorParse,
  isErrorExtract,
  onExtract,
  onNewExtraction,
  showTextPanel,
  showNoEntitiesNotice,
  displaySpans,
  setHover,
}) {
  return (
    <div className="flex-1 min-h-0 overflow-auto px-7 py-[22px]">
      <div className="flex items-center justify-between mb-3.5 gap-4">
        <div className="min-w-0">
          <div className="text-sm font-semibold break-all">
            {fileName || "document.pdf"}
          </div>
          <div className="text-xs text-[oklch(0.55_0.01_258)] mt-0.5">
            {fileMeta}
          </div>
        </div>
        {isParsed && (
          <div
            onClick={onExtract}
            className="shrink-0 flex items-center gap-2 px-5 py-[11px] rounded-lg bg-accent text-accent-ink text-[13.5px] font-semibold cursor-pointer"
          >
            Extract Entities
          </div>
        )}
        {isLoading && (
          <div className="shrink-0 flex items-center gap-2.5 px-5 py-[11px] rounded-lg bg-[oklch(0.28_0.02_252)] text-[oklch(0.75_0.02_252)] text-[13.5px] font-semibold">
            <Spinner size={14} border={2} /> Extracting…
          </div>
        )}
        {isResultsSuccess && (
          <div className="shrink-0 text-[12.5px] text-[oklch(0.6_0.01_258)] text-right">
            {entitiesCount} entities · {elapsedLabel}
          </div>
        )}
      </div>

      {isErrorParse && (
        <div className="border border-danger-border bg-danger-bg rounded-[10px] p-7 max-w-[520px]">
          <div className="text-sm font-semibold mb-2">
            Couldn't read this PDF
          </div>
          <div className="text-[13px] leading-relaxed text-[oklch(0.7_0.01_258)] mb-[18px]">
            The file may be encrypted, scanned as an image, or corrupted. Try a
            different PDF, or re-export the source document as text-based PDF.
          </div>
          <div
            onClick={onNewExtraction}
            className="inline-flex px-4 py-2 rounded-md bg-[oklch(0.3_0.015_258)] text-[13px] font-medium cursor-pointer border border-white/10"
          >
            Try a different file
          </div>
        </div>
      )}

      {isErrorExtract && (
        <div className="border border-danger-border bg-danger-bg rounded-[10px] px-5 py-4 mb-4 flex items-center justify-between gap-4">
          <div>
            <div className="text-[13.5px] font-semibold mb-1">
              Extraction failed
            </div>
            <div className="text-[12.5px] leading-normal text-[oklch(0.72_0.01_258)]">
              The model returned an unexpected response and structured entities
              couldn't be parsed. This is usually transient.
            </div>
          </div>
          <div
            onClick={onExtract}
            className="shrink-0 flex items-center px-4 py-[9px] rounded-[7px] bg-accent text-accent-ink text-[12.5px] font-semibold cursor-pointer"
          >
            Retry Extraction
          </div>
        </div>
      )}

      {showTextPanel && (
        <div>
          {showNoEntitiesNotice && (
            <div className="border border-white/10 bg-surface-3 rounded-lg px-4 py-3 text-[13px] text-[oklch(0.62_0.01_258)] mb-3.5">
              No entities were detected in this document. The text below is
              shown unhighlighted.
            </div>
          )}
          <div className="relative">
            <pre className="m-0 whitespace-pre-wrap break-words font-mono text-[12.5px] leading-[1.7] text-[oklch(0.85_0.006_258)] bg-surface-2 border border-white/8 rounded-[10px] px-6 py-[22px]">
              {displaySpans.map((seg) =>
                seg.isEntity ? (
                  <span
                    key={seg.key}
                    style={seg.style}
                    onMouseEnter={
                      seg.active
                        ? (e) =>
                            setHover({
                              label: seg.label,
                              value: seg.value,
                              x: e.clientX,
                              y: e.clientY,
                            })
                        : undefined
                    }
                    onMouseMove={
                      seg.active
                        ? (e) =>
                            setHover(
                              (h) => h && { ...h, x: e.clientX, y: e.clientY },
                            )
                        : undefined
                    }
                    onMouseLeave={() => setHover(null)}
                  >
                    {seg.text}
                  </span>
                ) : (
                  <span key={seg.key}>{seg.text}</span>
                ),
              )}
            </pre>
            {isLoading && (
              <div className="absolute inset-0 bg-[oklch(0.17_0.014_258_/_0.72)] backdrop-blur-[1px] rounded-[10px] flex flex-col items-center justify-center gap-3.5">
                <Spinner size={30} />
                <div className="text-[13px] font-mono text-[oklch(0.75_0.01_258)] animate-pulse-glow">
                  Analyzing document for entities…
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
