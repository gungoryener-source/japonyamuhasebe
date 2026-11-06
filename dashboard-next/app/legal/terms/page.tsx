import type { Metadata } from "next";
import { LegalPage } from "../../components/legal";
import { termsDoc, SELLER } from "../../lib/legal";

export const metadata: Metadata = { title: "利用規約 | J-SaaS 会計" };

export default function Page() {
  return <LegalPage doc={termsDoc(SELLER)} />;
}
