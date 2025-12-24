import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";

interface ChartData {
  day: string;
  manual: number;
  imported: number;
  total: number;
}

interface SpendingChartProps {
  data: ChartData[];
  primaryCurrency: string;
}

const SpendingChart = ({ data, primaryCurrency }: SpendingChartProps) => {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="colorManual" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="rgb(59, 130, 246)" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="rgb(59, 130, 246)" stopOpacity={0}/>
          </linearGradient>
          <linearGradient id="colorImported" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="rgb(168, 85, 247)" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="rgb(168, 85, 247)" stopOpacity={0}/>
          </linearGradient>
          <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.4}/>
            <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
        <XAxis 
          dataKey="day" 
          stroke="hsl(var(--muted-foreground))" 
          fontSize={12}
          tickLine={false}
        />
        <YAxis 
          stroke="hsl(var(--muted-foreground))" 
          fontSize={12}
          tickLine={false}
          tickFormatter={(value) => `${primaryCurrency} ${value}`}
        />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: 'hsl(var(--card))', 
            border: '1px solid hsl(var(--border))',
            borderRadius: '12px',
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
          }}
          formatter={(value: number) => [`${primaryCurrency} ${value.toFixed(2)}`, '']}
        />
        <Area 
          type="monotone" 
          dataKey="manual" 
          stroke="rgb(59, 130, 246)" 
          strokeWidth={2}
          fillOpacity={1} 
          fill="url(#colorManual)" 
          name="Manual"
        />
        <Area 
          type="monotone" 
          dataKey="imported" 
          stroke="rgb(168, 85, 247)" 
          strokeWidth={2}
          fillOpacity={1} 
          fill="url(#colorImported)" 
          name="Imported"
        />
        <Area 
          type="monotone" 
          dataKey="total" 
          stroke="hsl(var(--primary))" 
          strokeWidth={3}
          fillOpacity={1} 
          fill="url(#colorTotal)" 
          name="Total"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

export default SpendingChart;
