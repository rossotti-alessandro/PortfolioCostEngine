import { setLang } from "@/lib/i18n";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { NotStarted } from "./ReadSummary";

const html = (docs: { doc_type: string }[]) =>
  renderToStaticMarkup(
    <MemoryRouter>
      <NotStarted pid={1} docs={docs} />
    </MemoryRouter>,
  );

describe("NotStarted", () => {
  it("does not deny an uploaded statement whose positions could not be valued in CHF", () => {
    setLang("en");
    const out = html([{ doc_type: "portfolio_statement" }, { doc_type: "kid" }]);
    expect(out).toContain("A statement of assets is uploaded");
    expect(out).not.toContain("None of the");
  });
  it("asks for a statement when none is among the documents", () => {
    expect(html([{ doc_type: "kid" }])).toContain("None of the 1 documents is a statement of assets");
    expect(html([])).toContain("Upload a statement of assets for each bank to start.");
  });
});
