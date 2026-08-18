export function CurveChart({
  x,
  y,
  xLabel,
  yLabel,
  diagonal = false,
  size = 220,
}: {
  x: number[];
  y: number[];
  xLabel: string;
  yLabel: string;
  diagonal?: boolean;
  size?: number;
}) {
  const pad = 28;
  const inner = size - pad;
  const toX = (v: number) => pad + v * inner;
  const toY = (v: number) => size - pad - v * inner;

  const path = x.map((xi, i) => `${toX(xi)},${toY(y[i])}`).join(" ");

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <line x1={pad} y1={pad} x2={pad} y2={size - pad} stroke="#e2e8f0" />
      <line x1={pad} y1={size - pad} x2={size} y2={size - pad} stroke="#e2e8f0" />
      {diagonal && (
        <line x1={toX(0)} y1={toY(0)} x2={toX(1)} y2={toY(1)} stroke="#cbd5e1" strokeDasharray="3,3" />
      )}
      <polyline points={path} fill="none" stroke="#2748d8" strokeWidth="1.75" />
      <text x={pad} y={size - 8} fontSize="9" fill="#94a3b8">
        {xLabel}
      </text>
      <text x={4} y={pad - 8} fontSize="9" fill="#94a3b8">
        {yLabel}
      </text>
    </svg>
  );
}
