"use client";

import { useCallback, useEffect, useState } from "react";
import type { Mode } from "./shell";

/** Canlı modda `load()` çağırır, demo modunda `demo` değerini kullanır. */
export function useLoad<T>(mode: Mode, load: () => Promise<T>, demo: T, deps: unknown[] = []) {
  const [data, setData] = useState<T>(demo);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reload = useCallback(async () => {
    if (mode !== "live") { setData(demo); return; }
    setLoading(true);
    try {
      setData(await load());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, ...deps]);
  useEffect(() => { if (mode !== "loading") reload(); }, [mode, reload]);
  return { data, setData, loading, error, reload };
}
