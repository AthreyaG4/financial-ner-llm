import { colorOf } from "../data.js";

export default function Sidebar({
  sidebarOpen,
  setSidebarOpen,
  history,
  currentId,
  onNewExtraction,
  onSelectHistory,
}) {
  return (
    <div
      className={`${sidebarOpen ? "w-[240px]" : "w-[56px]"} shrink-0 h-full flex flex-col box-border border-r border-white/8 transition-[width] duration-150 ease-in-out overflow-hidden`}
    >
      {sidebarOpen ? (
        <div className="flex flex-col h-full p-3.5 gap-3">
          <div className="flex items-center justify-between">
            <div className="text-[10.5px] tracking-[0.06em] uppercase text-[oklch(0.48_0.01_258)] font-semibold">
              Extractions
            </div>
            <div
              onClick={() => setSidebarOpen(false)}
              className="cursor-pointer w-[22px] h-[22px] flex items-center justify-center rounded-[5px] text-[oklch(0.55_0.01_258)] text-[15px]"
            >
              ‹
            </div>
          </div>
          <div
            onClick={onNewExtraction}
            className="flex items-center justify-center gap-1.5 p-2.5 rounded-lg bg-accent text-accent-ink text-[13px] font-semibold cursor-pointer"
          >
            <span className="text-[15px] leading-none">+</span> New Extraction
          </div>
          <div className="flex-1 min-h-0 overflow-auto flex flex-col gap-1">
            {history.length === 0 ? (
              <div className="text-xs text-[oklch(0.42_0.01_258)] px-1 py-2.5 leading-normal">
                No extractions yet. Upload a document to get started.
              </div>
            ) : (
              history.map((h) => {
                const isActive = h.id === currentId;
                let statusColor = "oklch(0.55 0.01 258)",
                  statusLabel = "Ready to extract";
                if (h.stage === "results") {
                  const n = (h.entities || []).length;
                  statusColor = n ? colorOf("monetary") : "oklch(0.65 0.13 80)";
                  statusLabel = n ? n + " entities" : "No entities";
                } else if (h.stage === "errorParse") {
                  statusColor = "oklch(0.62 0.15 25)";
                  statusLabel = "Parse failed";
                } else if (h.stage === "errorExtract") {
                  statusColor = "oklch(0.62 0.15 25)";
                  statusLabel = "Extraction failed";
                } else if (h.stage === "loading") {
                  statusColor = "oklch(0.7 0.12 252)";
                  statusLabel = "Extracting…";
                }
                let time = "";
                try {
                  time = new Date(h.createdAt).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  });
                } catch (e) {}
                return (
                  <div
                    key={h.id}
                    onClick={() => onSelectHistory(h.id)}
                    className={`flex items-start gap-2.5 p-2 rounded-[7px] cursor-pointer ${isActive ? "bg-white/6 border border-white/10" : "bg-transparent border border-transparent"}`}
                  >
                    <div
                      className="w-[7px] h-[7px] rounded-full shrink-0 mt-[5px]"
                      style={{ background: statusColor }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-[12.5px] font-medium whitespace-nowrap overflow-hidden text-ellipsis">
                        {h.fileName}
                      </div>
                      <div className="text-[11px] text-[oklch(0.55_0.01_258)] mt-px">
                        {time} · {statusLabel}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2.5 pt-3.5">
          <div
            onClick={() => setSidebarOpen(true)}
            className="cursor-pointer w-[26px] h-[26px] flex items-center justify-center rounded-[5px] text-[oklch(0.55_0.01_258)] text-[15px]"
          >
            ›
          </div>
          <div
            onClick={onNewExtraction}
            className="cursor-pointer w-[26px] h-[26px] flex items-center justify-center rounded-md bg-accent text-accent-ink text-[15px] font-bold"
          >
            +
          </div>
        </div>
      )}
    </div>
  );
}
