import type { RouteObject } from "react-router-dom";
import BoardPage, { ContactsPage } from "./Board";
import ContactPage from "./Contact";
import FunnelPage from "./Funnel";

/** CRM routes, spread into the AppShell children in main.tsx. */
export const crmRoutes: RouteObject[] = [
  { path: "/crm", element: <BoardPage /> },
  { path: "/crm/list", element: <ContactsPage /> },
  { path: "/crm/funnel", element: <FunnelPage /> },
  { path: "/crm/c/:id", element: <ContactPage /> },
];
