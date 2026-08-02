export const ENTITY_META = {
  monetary: { label: "Monetary Amount", l: 0.75, c: 0.15, h: 150 },
  percentage: { label: "Percentage", l: 0.78, c: 0.15, h: 80 },
  date: { label: "Date", l: 0.75, c: 0.14, h: 230 },
  duration: { label: "Duration", l: 0.75, c: 0.13, h: 300 },
  other_number: { label: "Other Number", l: 0.75, c: 0.14, h: 20 },
};
export const TYPE_ORDER = [
  "monetary",
  "percentage",
  "date",
  "duration",
  "other_number",
];

export function colorOf(type) {
  const m = ENTITY_META[type];
  return `oklch(${m.l} ${m.c} ${m.h})`;
}
export function colorAlpha(type, a) {
  const m = ENTITY_META[type];
  return `oklch(${m.l} ${m.c} ${m.h} / ${a})`;
}

export function buildSpans(text, matches) {
  let cursor = 0;
  const spans = [];
  matches.forEach((m, i) => {
    const idx = text.indexOf(m.value, cursor);
    if (idx === -1) return;
    if (idx > cursor)
      spans.push({
        key: "p" + i,
        isEntity: false,
        text: text.slice(cursor, idx),
      });
    spans.push({
      key: "e" + i,
      isEntity: true,
      text: m.value,
      type: m.type,
      label: m.label,
      value: m.value,
    });
    cursor = idx + m.value.length;
  });
  if (cursor < text.length)
    spans.push({ key: "tail", isEntity: false, text: text.slice(cursor) });
  return spans;
}
