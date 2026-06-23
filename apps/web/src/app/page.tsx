import { IdentityOverview } from "@/features/identity/components/identity-overview";

export default function HomePage() {
  return (
    <div className="page-stack">
      <section className="hero">
        <p className="hero__eyebrow">Identity foundation</p>
        <h2>Connect the web app to Hify team context.</h2>
        <p>
          This first shell verifies the OpenAPI client, TanStack Query provider, and current actor
          contract before feature pages are added.
        </p>
      </section>
      <IdentityOverview />
    </div>
  );
}
