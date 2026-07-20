"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useSyncExternalStore } from "react";

const subscribe = (callback: () => void) => {
  window.addEventListener("storage", callback);
  window.addEventListener("themechange", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("themechange", callback);
  };
};

export function ThemeToggle() {
  const dark = useSyncExternalStore(
    subscribe,
    () => localStorage.getItem("theme") === "dark",
    () => false,
  );
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  const toggle = () => {
    const next = !dark;
    localStorage.setItem("theme", next ? "dark" : "light");
    document.documentElement.classList.toggle("dark", next);
    window.dispatchEvent(new Event("themechange"));
  };
  return (
    <button className="icon-button" onClick={toggle} aria-label="다크 모드 전환">
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
