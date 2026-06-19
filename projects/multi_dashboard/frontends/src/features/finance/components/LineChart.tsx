type Series = { key: string; label: string; color: string };

type Props<T extends Record<string, any>> = {
  data: T[];
  xKey: keyof T;
  series: Series[];
  height?: number;
};

export function LineChart<T extends Record<string, any>>({
  data,
  xKey,
  series,
  height = 300,
}: Props<T>) {
  const padding = { top: 16, right: 16, bottom: 28, left: 40 };
  const width = 800; // viewBox width; the SVG will scale responsively

  const xValues = data.map((d) => Number(d[xKey]));
  const yValues: number[] = [];
  for (const s of series) {
    for (const d of data) {
      const v = Number(d[s.key]);
      if (!Number.isNaN(v)) yValues.push(v);
    }
  }
  const xMin = Math.min(...xValues);
  const xMax = Math.max(...xValues);
  const yMin = Math.min(...yValues);
  const yMax = Math.max(...yValues);

  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  const xScale = (x: number) => {
    if (xMax === xMin) return padding.left;
    return padding.left + ((x - xMin) / (xMax - xMin)) * innerW;
  };

  const yScale = (y: number) => {
    if (yMax === yMin) return padding.top + innerH;
    return padding.top + innerH - ((y - yMin) / (yMax - yMin)) * innerH;
  };

  const makePath = (key: string) => {
    const pts = data.map((d) => ({ x: Number(d[xKey]), y: Number(d[key]) }));
    return pts
      .map(
        (p, i) =>
          `${i === 0 ? "M" : "L"} ${xScale(p.x).toFixed(2)} ${yScale(
            p.y
          ).toFixed(2)}`
      )
      .join(" ");
  };

  // Y axis ticks (5)
  const ticks = 5;
  const yTicks: number[] = [];
  for (let i = 0; i <= ticks; i++) {
    yTicks.push(yMin + ((yMax - yMin) * i) / ticks);
  }

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
      {/* Axes */}
      <line
        x1={padding.left}
        y1={padding.top}
        x2={padding.left}
        y2={padding.top + innerH}
        stroke="#94a3b8"
      />
      <line
        x1={padding.left}
        y1={padding.top + innerH}
        x2={padding.left + innerW}
        y2={padding.top + innerH}
        stroke="#94a3b8"
      />

      {/* Grid + Y labels */}
      {yTicks.map((t, i) => {
        const y = yScale(t);
        return (
          <g key={i}>
            <line
              x1={padding.left}
              y1={y}
              x2={padding.left + innerW}
              y2={y}
              stroke="#e2e8f0"
            />
            <text
              x={padding.left - 8}
              y={y}
              textAnchor="end"
              alignmentBaseline="middle"
              fontSize="10"
              fill="#64748b"
            >
              {t.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </text>
          </g>
        );
      })}

      {/* Series */}
      {series.map((s) => (
        <path
          key={s.key}
          d={makePath(s.key)}
          fill="none"
          stroke={s.color}
          strokeWidth={2}
        />
      ))}

      {/* Legend */}
      <g transform={`translate(${padding.left}, ${padding.top / 2})`}>
        {series.map((s, i) => (
          <g key={s.key} transform={`translate(${i * 130}, 0)`}>
            <rect width="14" height="3" y="-3" fill={s.color} />
            <text x="20" y="0" fontSize="12" fill="#334155">
              {s.label}
            </text>
          </g>
        ))}
      </g>
    </svg>
  );
}
