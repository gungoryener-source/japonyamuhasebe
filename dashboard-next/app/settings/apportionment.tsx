"use client";

/** 家事按分 — 勘定科目ごとの事業割合（損益・決算書・本則課税の仕入税額に反映。元の仕訳は変更しません） */
import { useEffect, useState } from "react";
import { Percent } from "lucide-react";
import { api } from "../lib/api";
import { useShell } from "../components/shell";
import { Btn, Card, inputCls, ReadOnlyNote } from "../components/ui";
import { useT } from "../components/lang";

const DEMO = ["地代家賃", "水道光熱費", "通信費", "消耗品費", "旅費交通費", "接待交際費", "雑費"].map((category) => ({ category, pct: category === "地代家賃" ? 40 : 100 }));

export function ApportionmentCard() {
  const { live, mode, toast, canEdit } = useShell();
  const t = useT();
  const [items, setItems] = useState(DEMO);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (mode === "loading" || !live) return;
    api.apportionment().then((r) => setItems(r.items)).catch(() => {});
  }, [mode, live]);

  const save = async () => {
    if (!live) return toast(t("保存しました（デモ）"));
    setBusy(true);
    try { setItems((await api.apportionmentPut(items)).items); toast(t("保存しました")); }
    catch (e) { toast(t("保存に失敗しました: {a}", { a: e instanceof Error ? e.message : String(e) })); }
    finally { setBusy(false); }
  };

  return (
    <Card title="家事按分" en="Business-use Ratio" right={<Percent size={16} className="text-mint" />} className="lg:col-span-2">
      <p className="text-[11px] leading-relaxed text-slate-400">
        {t("自宅兼事務所の家賃・光熱費・通信費など、私用と事業用が混在する科目の事業割合（%）。100% は按分なし。損益・青色申告決算書・本則課税の仕入税額に反映され、元の仕訳は変わりません。割合の根拠（面積・使用時間など）は保存しておいてください。")}
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {items.map((it, i) => (
          <label key={it.category} className="text-[11px] text-slate-500">
            {it.category}
            <input type="number" min={0} max={100} value={it.pct} disabled={!canEdit} aria-label={it.category}
              onChange={(e) => setItems(items.map((x, j) => (j === i ? { ...x, pct: Math.max(0, Math.min(100, Math.floor(Number(e.target.value) || 0))) } : x)))}
              className={inputCls + " tabular-nums"} />
          </label>
        ))}
      </div>
      {canEdit ? <Btn kind="primary" onClick={save} disabled={busy}>{t("保存")}</Btn>
        : <ReadOnlyNote>{t("閲覧者のため、変更はできません。")}</ReadOnlyNote>}
    </Card>
  );
}
