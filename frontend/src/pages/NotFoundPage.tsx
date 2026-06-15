import { Link } from "react-router-dom";

import { Button, PageHeader } from "@/components/ui";

export default function NotFoundPage() {
  return (
    <div className="page">
      <PageHeader title="Page not found" lede="That route doesn't exist in this build." />
      <Link to="/">
        <Button variant="primary" size="sm">
          Back to dashboard
        </Button>
      </Link>
    </div>
  );
}
