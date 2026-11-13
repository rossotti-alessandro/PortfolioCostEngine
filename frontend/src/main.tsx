import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Navigate, RouterProvider, createBrowserRouter } from "react-router-dom";
import { AppShell, ProspectLayout } from "./components/Shell";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/ibm-plex-mono/400.css";
import "./index.css";
import { useLang } from "./lib/i18n";
import CataloguePage from "./pages/Catalogue";
import ComparePage from "./pages/Compare";
import CostsPage from "./pages/Costs";
import DocumentsPage from "./pages/Documents";
import FirmTariffPage from "./pages/FirmTariff";
import HowItWorksPage from "./pages/HowItWorks";
import InternalPage from "./pages/Internal";
import { RequireAuth } from "./pages/Login";
import PipelinePage from "./pages/Pipeline";
import ProspectsPage from "./pages/Prospects";
import ReportPage from "./pages/Report";
import ReviewPage from "./pages/Review";
import { crmRoutes } from "./pages/crm/routes";

const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 10_000, retry: 1, refetchOnWindowFocus: false } },
});

const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/crm" replace /> },
      { path: "/prospects", element: <ProspectsPage /> },
      { path: "/catalogue", element: <CataloguePage /> },
      { path: "/how-it-works", element: <HowItWorksPage /> },
      { path: "/tariff", element: <FirmTariffPage /> },
      ...crmRoutes,
      {
        path: "/p/:id",
        element: <ProspectLayout />,
        children: [
          { index: true, element: <Navigate to="costs" replace /> },
          { path: "documents", element: <DocumentsPage /> },
          { path: "documents/:did", element: <PipelinePage /> },
          { path: "review", element: <ReviewPage /> },
          { path: "costs", element: <CostsPage /> },
          { path: "compare", element: <ComparePage /> },
          { path: "internal", element: <InternalPage /> },
          { path: "report", element: <ReportPage /> },
        ],
      },
      { path: "*", element: <Navigate to="/crm" replace /> },
    ],
  },
]);

/** Re-mounts the tree when the language changes, so every t() call re-renders. */
function Root() {
  const lang = useLang();
  return (
    <RequireAuth>
      <RouterProvider key={lang} router={router} />
    </RequireAuth>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <Root />
    </QueryClientProvider>
  </StrictMode>,
);
