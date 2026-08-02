export default function Header() {
  return (
    <div className="shrink-0 flex items-center justify-between px-6 py-3.5 border-b border-white/8">
      <div className="flex items-baseline gap-2.5">
        <div className="font-mono font-semibold text-[15px]">
          Entity Extractor
        </div>
        <div className="text-xs text-[oklch(0.5_0.01_258)]">
          Financial document analysis
        </div>
      </div>
    </div>
  );
}
