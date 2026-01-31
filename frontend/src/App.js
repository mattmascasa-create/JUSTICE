import React, { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { ThemeProvider } from "./contexts/ThemeContext";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { WebSocketProvider } from "./contexts/WebSocketContext";
import { Toaster } from "./components/ui/sonner";
import PanicButton from "./components/PanicButton";
import IncomingCallModal from "./components/IncomingCallModal";

// Loading Spinner Component for Suspense fallback
function PageLoader() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        <p className="text-muted-foreground text-sm">Loading...</p>
      </div>
    </div>
  );
}

// Critical pages loaded immediately (landing, auth, dashboard)
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import AuthCallback from "./pages/AuthCallback";
import Dashboard from "./pages/Dashboard";

// Quick Record - loads fast for PWA shortcut
import QuickRecordPage from "./pages/QuickRecordPage";

// Lazy loaded pages - Heavy/Feature-rich pages
const EncounterPageWithErrorBoundary = lazy(() => 
  import("./pages/EncounterPage").then(module => ({ 
    default: module.EncounterPageWithErrorBoundary 
  }))
);
const EncounterReportPage = lazy(() => import("./pages/EncounterReportPage"));
const CommunityMapPage = lazy(() => import("./pages/CommunityMapPage"));
const AccountabilityPortalPage = lazy(() => import("./pages/AccountabilityPortalPage"));
const PremiumAnalyticsPage = lazy(() => import("./pages/PremiumAnalyticsPage"));
const CourtGradeAIPage = lazy(() => import("./pages/CourtGradeAIPage"));
const AIAttorneyPage = lazy(() => import("./pages/AIAttorneyPage"));
const DocumentAnalysisPage = lazy(() => import("./pages/DocumentAnalysisPage"));
const AttorneyDashboardPage = lazy(() => import("./pages/AttorneyDashboardPage"));
const AttorneyEncounterWorkspacePage = lazy(() => import("./pages/AttorneyEncounterWorkspacePage"));
const ModerationDashboardPage = lazy(() => import("./pages/ModerationDashboardPage"));
const CustodyPortalPage = lazy(() => import("./pages/CustodyPortalPage"));
const PolicyDashboardPage = lazy(() => import("./pages/PolicyDashboardPage"));
const EncounterAnalytics = lazy(() => import("./pages/EncounterAnalytics"));
const VideoCallPage = lazy(() => import("./pages/VideoCallPage"));
const LiveStreamPage = lazy(() => import("./pages/LiveStreamPage"));
const SharedEncounterView = lazy(() => import("./pages/SharedEncounterView"));

// Lazy loaded pages - Secondary pages
const CasesPage = lazy(() => import("./pages/CasesPage"));
const CaseDetailPage = lazy(() => import("./pages/CaseDetailPage"));
const NewCasePage = lazy(() => import("./pages/NewCasePage"));
const EvidencePage = lazy(() => import("./pages/EvidencePage"));
const SOSPage = lazy(() => import("./pages/SOSPage"));
const AttorneysPage = lazy(() => import("./pages/AttorneysPage"));
const KnowYourRightsPage = lazy(() => import("./pages/KnowYourRightsPage"));
const MessagesPage = lazy(() => import("./pages/MessagesPage"));
const TransparencyPage = lazy(() => import("./pages/TransparencyPage"));
const IncidentMapPage = lazy(() => import("./pages/IncidentMapPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const CommunityVaultPage = lazy(() => import("./pages/CommunityVaultPage"));
const AttorneyAcceptInvitePage = lazy(() => import("./pages/AttorneyAcceptInvitePage"));
const RecordingsPage = lazy(() => import("./pages/RecordingsPage"));
const ScheduledReportsPage = lazy(() => import("./pages/ScheduledReportsPage"));
const ReportTemplatesPage = lazy(() => import("./pages/ReportTemplatesPage"));
const NotificationPreferencesPage = lazy(() => import("./pages/NotificationPreferencesPage"));
const AdvancedFeaturesPage = lazy(() => import("./pages/AdvancedFeaturesPage"));
const EmergencyContactsPage = lazy(() => import("./pages/EmergencyContactsPage"));
const WitnessNetworkPage = lazy(() => import("./pages/WitnessNetworkPage"));
const HardwareIntegrationPage = lazy(() => import("./pages/HardwareIntegrationPage"));
const TwoFactorSettingsPage = lazy(() => import("./pages/TwoFactorSettingsPage"));
const RightsTrainingPage = lazy(() => import("./pages/RightsTrainingPage"));
const LegalDocumentsPage = lazy(() => import("./pages/LegalDocumentsPage"));
const LegalToolsPage = lazy(() => import("./pages/LegalToolsPage"));

// Register service worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js')
      .then((registration) => {
        console.log('SW registered:', registration);
      })
      .catch((error) => {
        console.log('SW registration failed:', error);
      });
  });
}

// Protected Route Component
function ProtectedRoute({ children }) {
  const { user, loading, token, authError } = useAuth();
  const location = useLocation();

  if (loading) {
    return <PageLoader />;
  }

  // Check both user and token for authentication
  if (!user || !token) {
    console.log('[ProtectedRoute] Not authenticated - redirecting to login');
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Show error state if there's an auth error but we still have cached credentials
  if (authError) {
    console.log('[ProtectedRoute] Auth error detected:', authError);
  }

  return <WebSocketProvider>{children}</WebSocketProvider>;
}

// Suspense wrapper for lazy routes
function LazyRoute({ children }) {
  return (
    <Suspense fallback={<PageLoader />}>
      {children}
    </Suspense>
  );
}

// Protected + Lazy Route combo
function ProtectedLazyRoute({ children }) {
  return (
    <ProtectedRoute>
      <Suspense fallback={<PageLoader />}>
        {children}
      </Suspense>
    </ProtectedRoute>
  );
}

// App Router with OAuth handling
function AppRouter() {
  const location = useLocation();
  
  // Check URL fragment for session_id (OAuth callback)
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      {/* Public Routes - Critical (not lazy) */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      
      {/* Public Routes - Lazy loaded */}
      <Route path="/transparency" element={<LazyRoute><TransparencyPage /></LazyRoute>} />
      <Route path="/incident-map" element={<LazyRoute><IncidentMapPage /></LazyRoute>} />
      <Route path="/live/:encounterId" element={<LazyRoute><LiveStreamPage /></LazyRoute>} />
      <Route path="/shared/:encounterId" element={<LazyRoute><SharedEncounterView /></LazyRoute>} />
      <Route path="/attorney/accept-invite" element={<LazyRoute><AttorneyAcceptInvitePage /></LazyRoute>} />
      <Route path="/accountability" element={<LazyRoute><AccountabilityPortalPage /></LazyRoute>} />
      <Route path="/custody-portal" element={<LazyRoute><CustodyPortalPage /></LazyRoute>} />
      <Route path="/community-map" element={<LazyRoute><CommunityMapPage /></LazyRoute>} />
      
      {/* Protected Routes - Critical (Dashboard not lazy for fast access) */}
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      
      {/* Protected Routes - Heavy pages (Lazy loaded) */}
      <Route path="/encounter" element={<ProtectedLazyRoute><EncounterPageWithErrorBoundary /></ProtectedLazyRoute>} />
      <Route path="/encounters/:encounterId" element={<ProtectedLazyRoute><EncounterReportPage /></ProtectedLazyRoute>} />
      <Route path="/ai-attorney" element={<ProtectedLazyRoute><AIAttorneyPage /></ProtectedLazyRoute>} />
      <Route path="/analyze" element={<ProtectedLazyRoute><DocumentAnalysisPage /></ProtectedLazyRoute>} />
      <Route path="/policy" element={<ProtectedLazyRoute><PolicyDashboardPage /></ProtectedLazyRoute>} />
      <Route path="/analytics" element={<ProtectedLazyRoute><EncounterAnalytics /></ProtectedLazyRoute>} />
      <Route path="/attorney-dashboard" element={<ProtectedLazyRoute><AttorneyDashboardPage /></ProtectedLazyRoute>} />
      <Route path="/attorney/encounter/:encounterId" element={<ProtectedLazyRoute><AttorneyEncounterWorkspacePage /></ProtectedLazyRoute>} />
      <Route path="/premium-analytics" element={<ProtectedLazyRoute><PremiumAnalyticsPage /></ProtectedLazyRoute>} />
      <Route path="/court-grade-ai" element={<ProtectedLazyRoute><CourtGradeAIPage /></ProtectedLazyRoute>} />
      <Route path="/moderation" element={<ProtectedLazyRoute><ModerationDashboardPage /></ProtectedLazyRoute>} />
      <Route path="/call/:callId" element={<ProtectedLazyRoute><VideoCallPage /></ProtectedLazyRoute>} />
      
      {/* Protected Routes - Secondary pages (Lazy loaded) */}
      <Route path="/cases" element={<ProtectedLazyRoute><CasesPage /></ProtectedLazyRoute>} />
      <Route path="/cases/new" element={<ProtectedLazyRoute><NewCasePage /></ProtectedLazyRoute>} />
      <Route path="/cases/:caseId" element={<ProtectedLazyRoute><CaseDetailPage /></ProtectedLazyRoute>} />
      <Route path="/evidence" element={<ProtectedLazyRoute><EvidencePage /></ProtectedLazyRoute>} />
      <Route path="/community" element={<ProtectedLazyRoute><CommunityVaultPage /></ProtectedLazyRoute>} />
      <Route path="/sos" element={<ProtectedLazyRoute><SOSPage /></ProtectedLazyRoute>} />
      <Route path="/attorneys" element={<ProtectedLazyRoute><AttorneysPage /></ProtectedLazyRoute>} />
      <Route path="/messages" element={<ProtectedLazyRoute><MessagesPage /></ProtectedLazyRoute>} />
      <Route path="/rights" element={<ProtectedLazyRoute><KnowYourRightsPage /></ProtectedLazyRoute>} />
      <Route path="/settings" element={<ProtectedLazyRoute><SettingsPage /></ProtectedLazyRoute>} />
      <Route path="/recordings" element={<ProtectedLazyRoute><RecordingsPage /></ProtectedLazyRoute>} />
      <Route path="/scheduled-reports" element={<ProtectedLazyRoute><ScheduledReportsPage /></ProtectedLazyRoute>} />
      <Route path="/report-templates" element={<ProtectedLazyRoute><ReportTemplatesPage /></ProtectedLazyRoute>} />
      <Route path="/notification-preferences" element={<ProtectedLazyRoute><NotificationPreferencesPage /></ProtectedLazyRoute>} />
      <Route path="/advanced-features" element={<ProtectedLazyRoute><AdvancedFeaturesPage /></ProtectedLazyRoute>} />
      <Route path="/emergency-contacts" element={<ProtectedLazyRoute><EmergencyContactsPage /></ProtectedLazyRoute>} />
      <Route path="/witness-network" element={<ProtectedLazyRoute><WitnessNetworkPage /></ProtectedLazyRoute>} />
      <Route path="/hardware" element={<ProtectedLazyRoute><HardwareIntegrationPage /></ProtectedLazyRoute>} />
      <Route path="/security/2fa" element={<ProtectedLazyRoute><TwoFactorSettingsPage /></ProtectedLazyRoute>} />
      <Route path="/training" element={<ProtectedLazyRoute><RightsTrainingPage /></ProtectedLazyRoute>} />
      <Route path="/legal-documents" element={<ProtectedLazyRoute><LegalDocumentsPage /></ProtectedLazyRoute>} />
      <Route path="/legal-tools" element={<ProtectedLazyRoute><LegalToolsPage /></ProtectedLazyRoute>} />
      
      {/* Auth Callback */}
      <Route path="/auth/callback" element={<AuthCallback />} />
      
      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppRouter />
          <IncomingCallModal />
          <PanicButton />
          <Toaster position="top-right" richColors />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
