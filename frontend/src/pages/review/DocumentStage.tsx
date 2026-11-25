/** The source page: the work surface. It fills the stage; the page image scrolls inside it. */

import { PdfEvidence, SheetEvidence } from "@/components/EvidenceViewer";
import { Badge, Card, Spinner } from "@/components/ui";
import { t } from "@/lib/i18n";
import { isOcrEngine } from "@/lib/trail";
import type { DocumentRow, Fact } from "@/lib/types";
import { ScanLine } from "lucide-react";
import { DocumentSwitcher } from "./DocumentSwitcher";

export function DocumentStage({
  docs,
  doc,
  docId,
  onSelectDoc,
  facts,
  activeId,
  activePage,
  isSheet,
  onSelectFact,
}: {
  docs: DocumentRow[];
  doc: DocumentRow | undefined;
  docId: number | undefined;
  onSelectDoc: (id: number) => void;
  facts: Fact[] | undefined;
  activeId: number | null;
  activePage: number | undefined;
  isSheet: boolean;
  onSelectFact: (f: Fact) => void;
}) {
  return (
    <Card data-review="stage" className="flex h-[70vh] min-h-[24rem] flex-col overflow-hidden xl:h-full xl:min-h-0">
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-line px-4 py-2">
        <DocumentSwitcher docs={docs} docId={docId} onSelect={onSelectDoc} />
        {doc?.profile.engines.some(isOcrEngine) && (
          <Badge tone="violet">
            <ScanLine className="h-3 w-3" /> {t("Scanned · OCR")}
          </Badge>
        )}
      </div>
      <div className="min-h-0 flex-1">
        {!docId || !facts ? (
          <Spinner label={t("Opening document")} />
        ) : isSheet ? (
          <SheetEvidence docId={docId} facts={facts} activeId={activeId} onSelect={onSelectFact} />
        ) : (
          <PdfEvidence docId={docId} facts={facts} activeId={activeId} page={activePage} onSelect={onSelectFact} />
        )}
      </div>
    </Card>
  );
}
