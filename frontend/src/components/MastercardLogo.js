export default function MastercardLogo({ size = 40 }) {
  const r = size / 2;
  const overlap = size * 0.3;
  return (
    <div className="flex items-center gap-2">
      <svg
        width={size * 2 - overlap}
        height={size}
        viewBox={`0 0 ${size * 2 - overlap} ${size}`}
      >
        <circle cx={r} cy={r} r={r} fill="#EB001B" />
        <circle cx={size - overlap + r} cy={r} r={r} fill="#F79E1B" opacity="0.9" />
      </svg>
      <span className="text-white font-semibold text-base tracking-wide">mastercard</span>
    </div>
  );
}
