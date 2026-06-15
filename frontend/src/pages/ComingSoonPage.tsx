import { PageHeader } from "@/components/ui";
import { I } from "@/components/icons";

export default function ComingSoonPage({ title, lede }: { title: string; lede?: string }) {
  return (
    <div className="page">
      <PageHeader eyebrow="In progress" title={title} lede={lede} />
      <div className="empty">
        <I.sparkle size={28} />
        <div className="title">{title} is coming soon</div>
        <div className="lede">
          The backend module exists and is reachable through the API; the dedicated UI is being built
          in upcoming sessions. See <code>handoff.md</code> for the full roadmap.
        </div>
      </div>
    </div>
  );
}
