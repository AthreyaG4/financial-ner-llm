import { colorOf } from "../data.js";

export default function EntityLegend({
  hasLegend,
  legendItems,
  onToggleFilter,
}) {
  return (
    <div className="w-[280px] shrink-0 border-l border-white/8 p-[18px] overflow-auto">
      <div className="text-[10.5px] tracking-[0.06em] uppercase text-[oklch(0.48_0.01_258)] font-semibold mb-3">
        Entity Types
      </div>
      {hasLegend ? (
        <div className="flex flex-col gap-[3px]">
          {legendItems.map((item) => (
            <div
              key={item.type}
              onClick={() => onToggleFilter(item.type)}
              className={`flex items-center gap-2.5 px-2 py-[7px] rounded-md cursor-pointer ${item.active ? "opacity-100 bg-white/3" : "opacity-45 bg-transparent"}`}
            >
              <div
                className="w-[9px] h-[9px] rounded-full shrink-0"
                style={{
                  background: item.active
                    ? colorOf(item.type)
                    : "oklch(0.4 0.01 258)",
                }}
              />
              <div className="flex-1 text-[12.5px]">{item.label}</div>
              <div className="text-[11.5px] font-mono text-[oklch(0.55_0.01_258)]">
                {item.count}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-[12.5px] text-[oklch(0.45_0.01_258)] leading-relaxed">
          No entities detected for this document.
        </div>
      )}
    </div>
  );
}
