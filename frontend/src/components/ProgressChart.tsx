import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from 'recharts';

interface Props {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[];
  lines: Array<{ key: string; color: string; name: string }>;
  xKey?: string;
}

export default function ProgressChart({ data, lines, xKey = 'date' }: Props) {
  if (data.length === 0) {
    return <div className="empty">Keine Daten vorhanden</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: -10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis
          dataKey={xKey}
          tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
          tickFormatter={v => {
            const d = new Date(v);
            return `${d.getDate()}.${d.getMonth() + 1}`;
          }}
        />
        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
        <Tooltip
          contentStyle={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            color: 'var(--text)',
          }}
        />
        <Legend />
        {lines.map(l => (
          <Line
            key={l.key}
            type="monotone"
            dataKey={l.key}
            stroke={l.color}
            name={l.name}
            dot={false}
            strokeWidth={2}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
