---
id: SC-8.28
title: Scan documents with the phone camera and upload photos
status: Done
assignee: []
owner: "Rebuild CRM for mobile and browser"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-m6dkdk"
pr: ""
created_date: "2026-11-25 19:55"
updated_date: "2026-11-25 19:43"
labels:
  - ui
  - intake
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - "backend/src/pce/api.py"
  - "backend/src/pce/scan_upload.py"
  - "backend/tests/test_scan_upload.py"
  - "frontend/src/pages/Documents.tsx"
  - "frontend/src/components/ScanDialog.tsx"
  - "frontend/src/lib/photos.ts"
  - "frontend/src/lib/photos.test.ts"
  - "frontend/src/lib/api.ts"
  - "frontend/src/lib/it.ts"
  - "frontend/tests/e2e/scan.spec.ts"
spec_ref: docs/research/UX_RECOMMENDATIONS.md
rule_refs:
  - ".claude/rules/frontend.md"
  - ".claude/rules/privacy.md"
  - ".claude/rules/extraction.md"
---

> **One-liner**: On a phone the analyst taps "Scan with camera", shoots one or more pages of a paper document, and FeeLens stores them as one PDF that the existing OCR path reads; photos (JPEG/PNG) can also be uploaded or dropped like PDFs.

## Description

### Context

Uploads accept only PDF and XLSX (`pce.api.ALLOWED`). A prospect often brings paper statements; the
analyst has a phone, not a scanner. Ale asked (2026-11-25) for camera capture on mobile.

### User Flow Impact

Documents page: a "Scan with camera" button next to "Choose files". It opens a dialog: take a page,
see thumbnails, retake/remove/reorder, add more pages, then "Save as one document". Each photo is
shrunk on the phone before upload (faster on mobile data). Photos chosen or dropped one by one become
one document each.

### Performance / Efficiency Impact

Phone photos (3-12 MB) are resized in the browser to at most 2400 px on the long side, JPEG 0.85:
about 0.5-1 MB per page. OCR time per page is unchanged.

### Proposed Approach

1. `pce/scan_upload.py`: `photos_to_pdf(pages: list[bytes]) -> bytes`. Uses the accuracy thread's
   `pce.extraction.photo` cleanup (rotation, crop, deskew, lighting) when present; otherwise Pillow:
   EXIF transpose, RGB, one PDF page per photo at 300 dpi. Bytes sniffed with libmagic; max 30 pages.
2. `POST /api/prospects/{id}/documents`: JPEG/PNG accepted; `combine=true` turns all photos of the
   request into one PDF. The stored file is the PDF; the original photos are not kept.
3. Frontend `lib/photos.ts` (resize/re-encode, also turns iPhone HEIC into JPEG where the browser can
   decode it) and `components/ScanDialog.tsx` using `<input capture="environment">` (the phone's own
   camera app: works on iOS and Android, no camera permission for the site, no Permissions-Policy change).

### Risks & Follow-ups

Live in-page camera with edge detection (getUserMedia) is a follow-up; it needs `camera=(self)` in the
Permissions-Policy. Handwriting is out of scope here (accuracy thread).

## Acceptance Criteria

- [x] #1 Three synthetic page photos uploaded with combine=true become one 3-page PDF document that is OCR-read
- [x] #2 A file that claims .jpg but is not an image is refused; PDF/XLSX uploads behave as before (regression guard)

## Implementation Notes

- Backend: `pce/scan_upload.py` (`photos_to_pdf`, Pillow fallback; uses `pce.extraction.photo.images_to_pdf`
  automatically once the accuracy thread merges it). `upload` gained `combine` and `scan_name` form fields;
  photos are sniffed with libmagic, max 40 MP each, max 30 pages per scan.
- Frontend: `lib/photos.ts` shrinks to 2400 px JPEG 0.85 (also HEIC on Safari, drops EXIF location);
  `components/ScanDialog.tsx` (camera via `capture="environment"`, gallery, reorder, remove, name).
- Documents page grid fixed: it scrolled sideways on a 390 px phone (min-width of the grid column).

## Outcome

- **Status**: completed
- pytest 4 new tests (incl. 3-photo scan read by OCR, EXIF rotation, fake photo refused); vitest 3 new;
  Playwright `scan.spec.ts` on a 390 px phone: 2 pages shot, reordered, named, saved as one 2-page PDF.
- Full gate GATE PASSED; Playwright 24/24.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-m6dkdk | 40a956b | 2026-11-25 | camera scan, photo upload, phone layout fix |
