"use client";

import type { PointerEvent, ReactNode } from "react";
import { useRef, useState } from "react";

export function DragScroll({ children, className = "" }: { children: ReactNode; className?: string }) {
  const elementRef = useRef<HTMLDivElement>(null);
  const origin = useRef({ x: 0, y: 0, left: 0, top: 0 });
  const [dragging, setDragging] = useState(false);

  const start = (event: PointerEvent<HTMLDivElement>) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    if ((event.target as HTMLElement).closest("a, button, input, select, textarea")) return;
    const element = elementRef.current;
    if (!element) return;
    origin.current = { x: event.clientX, y: event.clientY, left: element.scrollLeft, top: element.scrollTop };
    element.setPointerCapture(event.pointerId);
    setDragging(true);
  };
  const move = (event: PointerEvent<HTMLDivElement>) => {
    if (!dragging || !elementRef.current) return;
    elementRef.current.scrollLeft = origin.current.left - (event.clientX - origin.current.x);
    elementRef.current.scrollTop = origin.current.top - (event.clientY - origin.current.y);
  };
  const stop = (event: PointerEvent<HTMLDivElement>) => {
    if (elementRef.current?.hasPointerCapture(event.pointerId)) {
      elementRef.current.releasePointerCapture(event.pointerId);
    }
    setDragging(false);
  };

  return (
    <div
      className={`drag-scroll ${dragging ? "is-dragging" : ""} ${className}`}
      onPointerCancel={stop}
      onPointerDown={start}
      onPointerMove={move}
      onPointerUp={stop}
      ref={elementRef}
    >
      {children}
    </div>
  );
}
