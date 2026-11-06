import type { Metadata } from "next";
import { LegalPage } from "../../components/legal";
import { tokushohoDoc, SELLER } from "../../lib/legal";

export const metadata: Metadata = { title: "特定商取引法に基づく表記 | J-SaaS 会計" };

export default function Page() {
  return <LegalPage doc={tokushohoDoc(SELLER)} />;
}
