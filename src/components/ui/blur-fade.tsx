"use client";

import { useEffect, useRef, useState } from "react";

interface BlurFadeProps {
  children: React.ReactNode;
  className?: string;
  duration?: number;
  delay?: number;
  offset?: number;
  direction?: "up" | "down" | "left" | "right";
  inView?: boolean;
  inViewMargin?: string;
  blur?: string;
}

const axisMap = {
  up: "translateY(1)",
  down: "translateY(-1)",
  left: "translateX(1)",
  right: "translateX(-1)",
};

export function BlurFade({
  children,
  className,
  duration = 0.4,
  delay = 0,
  offset = 6,
  direction = "down",
  inView = false,
  inViewMargin = "0px",
  blur = "6px",
}: BlurFadeProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [visible, setVisible] = useState(!inView);

  useEffect(() => {
    if (!inView || !ref.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && setVisible(true),
      { rootMargin: inViewMargin }
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [inView, inViewMargin]);

  const transformAxis = direction === "left" || direction === "right" ? "X" : "Y";
  const directionMultiplier = direction === "right" || direction === "down" ? -1 : 1;

  const initialTransform = `translate${transformAxis}(${directionMultiplier * offset}px)`;

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translate(0,0)" : initialTransform,
        filter: visible ? "blur(0px)" : `blur(${blur})`,
        transition: `all ${duration}s ease ${delay}s`,
      }}
    >
      {children}
    </div>
  );
}

export default BlurFade;
