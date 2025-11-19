import { useEffect, useRef, useState } from "react";

type NumberTickerProps = {
  value: number;
  duration?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
};

/**
 * Pequeno componente inspirado no "number-ticker" do Magic UI.
 * Faz a contagem animada de um número até o valor informado.
 */
export const NumberTicker = ({
  value,
  duration = 1200,
  decimals = 0,
  prefix = "",
  suffix = "",
}: NumberTickerProps) => {
  const [displayValue, setDisplayValue] = useState(0);
  const rafRef = useRef<number>();

  useEffect(() => {
    const start = performance.now();

    const animate = (timestamp: number) => {
      const elapsed = timestamp - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      setDisplayValue(value * eased);
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    };

    rafRef.current = requestAnimationFrame(animate);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [value, duration]);

  const formatted = `${prefix}${displayValue.toFixed(decimals)}${suffix}`;
  return <span className="font-semibold tabular-nums">{formatted}</span>;
};

export default NumberTicker;
