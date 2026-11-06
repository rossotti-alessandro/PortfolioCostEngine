import { Badge, Button, Card, Dialog, Empty, ErrorBox, Field, Spinner, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { BOUND_TEXT, bps, chf } from "@/lib/format";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Building2, FlaskConical, Plus, Upload } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function ProspectsPage() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ["prospects"], queryFn: api.prospects });
  const seed = useMutation({
    mutationFn: api.seed,
    onSuccess: (r) => {
      qc.invalidateQueries();
      nav(`/p/${r.id}/costs`);
    },
  });
  const [open, setOpen] = useState(false);
  return (
    <div className="mx-auto max-w-[1200px] px-4 py-6 sm:px-8">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-navy-900">Prospects</h1>
          <p className="mt-1 max-w-2xl text-[13.5px] text-muted">
            Upload a prospect's bank and product documents to see what their portfolio really costs today, with every
            number traced to its source, and how a proposal compares.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => seed.mutate()} loading={seed.isPending}>
            <FlaskConical className="h-4 w-4" /> Load synthetic demo
          </Button>
          <Button onClick={() => setOpen(true)}>
            <Plus className="h-4 w-4" /> New prospect
          </Button>
        </div>
      </div>
      {seed.error && <ErrorBox error={seed.error} />}
      <Card>
        {isLoading ? (
          <Spinner />
        ) : error ? (
          <ErrorBox error={error} />
        ) : !data?.length ? (
          <Empty icon={<Building2 className="h-8 w-8" />} title="No prospects yet">
            Create a prospect and upload their statements, or load the synthetic two-bank demo to explore the workflow.
            <div className="mt-4 flex justify-center gap-2">
              <Button variant="accent" onClick={() => seed.mutate()} loading={seed.isPending}>
                <FlaskConical className="h-4 w-4" /> Load synthetic demo
              </Button>
            </div>
          </Empty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13.5px]">
              <thead>
                <tr className="border-b border-line text-left text-[12px] uppercase tracking-wide text-subtle">
                  <th className="px-5 py-2.5 font-medium">Prospect</th>
                  <th className="px-3 py-2.5 text-right font-medium">Assets</th>
                  <th className="px-3 py-2.5 text-right font-medium">Known annual cost</th>
                  <th className="px-3 py-2.5 font-medium">Evidence</th>
                  <th className="px-3 py-2.5 text-right font-medium">Saving (same holdings)</th>
                  <th className="px-3 py-2.5 font-medium">Report</th>
                  <th className="px-5 py-2.5" />
                </tr>
              </thead>
              <tbody>
                {data.map((p) => (
                  <tr
                    key={p.id}
                    className="cursor-pointer border-b border-line last:border-0 hover:bg-paper/60"
                    tabIndex={0}
                    onClick={() => nav(p.documents ? `/p/${p.id}/costs` : `/p/${p.id}/documents`)}
                    onKeyDown={(e) =>
                      e.key === "Enter" && nav(p.documents ? `/p/${p.id}/costs` : `/p/${p.id}/documents`)
                    }
                  >
                    <td className="px-5 py-3">
                      <div className="font-medium text-navy-900">{p.label}</div>
                      <div className="mt-0.5 flex items-center gap-2 text-[12px] text-subtle">
                        {p.code} · {p.documents} documents · domicile {p.domicile}
                        {p.synthetic && <Badge tone="amber">Synthetic</Badge>}
                      </div>
                    </td>
                    <td className="num px-3 py-3 text-right">{p.summary ? chf(p.summary.aum) : "–"}</td>
                    <td className="num px-3 py-3 text-right">
                      {p.summary ? (
                        <>
                          {chf(p.summary.current_known)}
                          <div className="text-[12px] text-subtle">{bps(p.summary.current_bps)}</div>
                        </>
                      ) : (
                        "–"
                      )}
                    </td>
                    <td className="px-3 py-3">
                      {!p.summary ? (
                        <Badge>Awaiting documents</Badge>
                      ) : p.summary.complete ? (
                        <Badge tone="teal">Complete</Badge>
                      ) : (
                        <Badge tone="amber">{p.summary.open_requests} documents requested</Badge>
                      )}
                    </td>
                    <td className="num px-3 py-3 text-right">
                      {p.summary ? (
                        <>
                          <span className="text-[12px] text-subtle">{BOUND_TEXT[p.summary.bound]} </span>
                          <span className={Number(p.summary.saving) > 0 ? "font-medium text-teal-700" : ""}>
                            {chf(p.summary.saving)}
                          </span>
                        </>
                      ) : (
                        "–"
                      )}
                    </td>
                    <td className="px-3 py-3">
                      {p.summary?.approved ? <Badge tone="teal">Approved</Badge> : <Badge>Draft</Badge>}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <ArrowRight className="ml-auto h-4 w-4 text-subtle" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {[
          [
            "1 · Upload",
            "Statements of assets, annual cost reports, cash statements, fee agreements and KIDs from any bank. PDF (digital or scanned) and Excel.",
          ],
          [
            "2 · Verify",
            "Every number is extracted with its page and position. Analysts accept or correct it; missing costs stay visible as unknown.",
          ],
          [
            "3 · Compare",
            "Same-holdings comparison against your fee and custodian schedule, switching costs and payback, then a client-ready report.",
          ],
        ].map(([t, d]) => (
          <div
            key={t}
            className="rounded-[var(--radius-card)] border border-dashed border-line-strong bg-surface/60 p-4"
          >
            <div className="text-[13px] font-semibold text-navy-900">{t}</div>
            <p className="mt-1 text-[12.5px] leading-relaxed text-muted">{d}</p>
          </div>
        ))}
      </div>
      <NewProspectDialog open={open} onOpenChange={setOpen} />
    </div>
  );
}

function NewProspectDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [code, setCode] = useState("");
  const [label, setLabel] = useState("");
  const [domicile, setDomicile] = useState("CH");
  const m = useMutation({
    mutationFn: () => api.createProspect({ code, label, domicile }),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["prospects"] });
      onOpenChange(false);
      nav(`/p/${r.id}/documents`);
    },
  });
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="New prospect"
      description="Use a pseudonymous code. Names and account numbers are not needed for the cost review."
    >
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
      >
        <Field label="Prospect code" hint="e.g. P-1043. Must be unique.">
          <input className={inputCls} value={code} onChange={(e) => setCode(e.target.value)} required maxLength={64} />
        </Field>
        <Field label="Display name" hint="Pseudonym or initials only.">
          <input
            className={inputCls}
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            required
            maxLength={200}
          />
        </Field>
        <Field label="Client tax domicile" hint="Decides whether Swiss VAT applies to proposed fees.">
          <select className={inputCls} value={domicile} onChange={(e) => setDomicile(e.target.value)}>
            <option value="CH">Switzerland (CH)</option>
            <option value="IT">Italy (IT)</option>
            <option value="DE">Germany (DE)</option>
            <option value="FR">France (FR)</option>
            <option value="GB">United Kingdom (GB)</option>
            <option value="US">United States (US)</option>
          </select>
        </Field>
        {m.error && <ErrorBox error={m.error} />}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" loading={m.isPending}>
            <Upload className="h-4 w-4" /> Create and upload documents
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
