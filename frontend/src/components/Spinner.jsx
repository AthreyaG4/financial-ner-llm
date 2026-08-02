export default function Spinner({ size = 28, border = 3 }) {
  return (
    <div
      className="rounded-full border-white/14 border-t-accent-light animate-spin-fast"
      style={{ width: size, height: size, borderWidth: border }}
    />
  );
}
