export interface RadarAxis {
  label: string;
  value: number; // normalized 0-1
}

export function RadarChart({ axes, size = 220 }: { axes: RadarAxis[]; size?: number }) {
  const center = size / 2;
  const radius = size / 2 - 28;
  const n = axes.length;

  const pointFor = (i: number, value: number) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const r = radius * Math.max(0, Math.min(1, value));
    return [center + r * Math.cos(angle), center + r * Math.sin(angle)];
  };

  const dataPoints = axes.map((a, i) => pointFor(i, a.value));
  const dataPath = dataPoints.map((p) => p.join(",")).join(" ");

  const rings = [0.25, 0.5, 0.75, 1];

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {rings.map((r) => (
        <polygon
          key={r}
          points={axes.map((_, i) => pointFor(i, r).join(",")).join(" ")}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="1"
        />
      ))}
      {axes.map((_, i) => {
        const [x, y] = pointFor(i, 1);
        return <line key={i} x1={center} y1={center} x2={x} y2={y} stroke="#e2e8f0" strokeWidth="1" />;
      })}
      <polygon points={dataPath} fill="#3763f4" fillOpacity="0.25" stroke="#2748d8" strokeWidth="1.5" />
      {dataPoints.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="2.5" fill="#2748d8" />
      ))}
      {axes.map((a, i) => {
        const [x, y] = pointFor(i, 1.22);
        return (
          <text
            key={a.label}
            x={x}
            y={y}
            fontSize="10"
            fill="#64748b"
            textAnchor="middle"
            dominantBaseline="middle"
          >
            {a.label}
          </text>
        );
      })}
    </svg>
  );
}
