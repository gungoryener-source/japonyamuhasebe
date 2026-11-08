"use client";

/** 申告前チェックリスト — 帳簿から機械的に拾える抜け漏れ（T-081）。税額の判断はせず、確認候補を出す。 */
import { useEffect, useState } from "react";
import { CircleCheck, Info, TriangleAlert } from "lucide-react";
import { api, type ApiPrecheck } from "../lib/api";
import { Badge, Card } from "../components/ui";
import { T } from "../lib/i18n";

const DEMO = (year: number): ApiPrecheck => ({
  year, warn_count: 1,
  items: [
    { key: "no_invoice_no", level: "warn", message: "登録番号のない課税仕入が2件あります。経過措置（80%・70%など）の対象か確認してください。", count: 2, link: "/expenses/" },
    { key: "apportion_unset", level: "info", message: "地代家賃の家事按分が未設定（100%＝全額事業用）です。私用分がないか確認してください。", count: 0, link: "/settings/" },
    { key: "disclaimer", level: "info", message: "これは帳簿データからの確認候補です。申告前に税理士・税務署に確認してください。", count: 0, link: "" },
  ],
});

export default function Precheck({ year, live }: { year: number; live: boolean }) {
  const [data, setData] = useState<ApiPrecheck>(DEMO(year));
  useEffect(() => {
    if (!live) { setData(DEMO(year)); return; }
    let off = false;
    api.precheck(year).then((d) => { if (!off) setData(d); }).catch(() => {});
    return () => { off = true; };
  }, [year, live]);

  return (
    <Card title="申告前チェックリスト" en="Pre-filing Check"
      right={data.warn_count ? <Badge tone="warn">{T("要確認 {a} 件", { a: data.warn_count })}</Badge> : <Badge tone="ok">{T("問題なし")}</Badge>}>
      <ul className="divide-y divide-slate-100">
        {data.items.map((i) => (
          <li key={i.key} className="flex items-start gap-2 py-2 text-xs">
            {i.level === "warn" ? <TriangleAlert size={14} className="mt-0.5 shrink-0 text-amber-500" />
              : i.level === "ok" ? <CircleCheck size={14} className="mt-0.5 shrink-0 text-mint" />
                : <Info size={14} className="mt-0.5 shrink-0 text-slate-400" />}
            <span className="flex-1 text-slate-700">{i.message}</span>
            {i.link && <a href={i.link} className="shrink-0 text-[11px] text-mint-700 hover:underline">{T("開く")}</a>}
          </li>
        ))}
      </ul>
    </Card>
  );
}
