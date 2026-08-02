export default function HoverTooltip({ hover }) {
  if (!hover) return null;
  return (
    <div
      className="fixed z-50 bg-[oklch(0.24_0.014_258)] border border-white/14 rounded-lg px-3 py-2 shadow-[0_8px_24px_rgba(0,0,0,0.4)] pointer-events-none"
      style={{ left: hover.x + 14, top: hover.y + 18 }}
    >
      <div className="text-[10px] tracking-[0.04em] uppercase text-[oklch(0.6_0.01_258)] mb-[3px]">
        {hover.label}
      </div>
      <div className="text-[13px] font-semibold font-mono">{hover.value}</div>
    </div>
  );
}
