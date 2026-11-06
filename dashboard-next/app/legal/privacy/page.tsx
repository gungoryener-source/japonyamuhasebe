import type { Metadata } from "next";
import { LegalPage } from "../../components/legal";
import { privacyDoc, SELLER } from "../../lib/legal";

export const metadata: Metadata = { title: "プライバシーポリシー | J-SaaS 会計" };

export default function Page() {
  return <LegalPage doc={privacyDoc(SELLER)} />;
}
