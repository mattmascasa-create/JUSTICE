import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { ThemeProvider } from "./contexts/ThemeContext";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { WebSocketProvider } from "./contexts/WebSocketContext";
import { Toaster } from "./components/ui/sonner";

// Pages
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import AuthCallback from "./pages/AuthCallback";
import Dashboard from "./pages/Dashboard";
import CasesPage from "./pages/CasesPage";
import CaseDetailPage from "./pages/CaseDetailPage";
import NewCasePage from "./pages/NewCasePage";
import EvidencePage from "./pages/EvidencePage";
import AIAttorneyPage from "./pages/AIAttorneyPage";
import SOSPage from "./pages/SOSPage";
import AttorneysPage from "./pages/AttorneysPage";
import KnowYourRightsPage from "./pages/KnowYourRightsPage";
import MessagesPage from "./pages/MessagesPage";
import TransparencyPage from "./pages/TransparencyPage";
import IncidentMapPage from "./pages/IncidentMapPage";
import SettingsPage from "./pages/SettingsPage";
import EncounterPage from "./pages/EncounterPage";
import EncounterReportPage from "./pages/EncounterReportPage";
import LiveStreamPage from "./pages/LiveStreamPage";
import DocumentAnalysisPage from "./pages/DocumentAnalysisPage";
import CommunityVaultPage from "./pages/CommunityVaultPage";
import PolicyDashboardPage from "./pages/PolicyDashboardPage";
import EncounterAnalytics from "./pages/EncounterAnalytics";
import SharedEncounterView from "./pages/SharedEncounterView";
import AttorneyDashboardPage from "./pages/AttorneyDashboardPage";
import AttorneyAcceptInvitePage from "./pages/AttorneyAcceptInvitePage";
import AttorneyEncounterWorkspacePage from "./pages/AttorneyEncounterWorkspacePage";
import VideoCallPage from "./pages/VideoCallPage";
import IncomingCallModal from "./components/IncomingCallModal";
import RecordingsPage from "./pages/RecordingsPage";
import ScheduledReportsPage from "./pages/ScheduledReportsPage";
import ReportTemplatesPage from "./pages/ReportTemplatesPage";
import NotificationPreferencesPage from "./pages/NotificationPreferencesPage";
import AdvancedFeaturesPage from "./pages/AdvancedFeaturesPage";
import EmergencyContactsPage from "./pages/EmergencyContactsPage";
import WitnessNetworkPage from "./pages/WitnessNetworkPage";

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
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <WebSocketProvider>{children}</WebSocketProvider>;
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
      {/* Public Routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/transparency" element={<TransparencyPage />} />
      <Route path="/incident-map" element={<IncidentMapPage />} />
      <Route path="/live/:encounterId" element={<LiveStreamPage />} />
      <Route path="/shared/:encounterId" element={<SharedEncounterView />} />
      <Route path="/attorney/accept-invite" element={<AttorneyAcceptInvitePage />} />
      
      {/* Protected Routes */}
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/encounter" element={<ProtectedRoute><EncounterPage /></ProtectedRoute>} />
      <Route path="/encounters/:encounterId" element={<ProtectedRoute><EncounterReportPage /></ProtectedRoute>} />
      <Route path="/cases" element={<ProtectedRoute><CasesPage /></ProtectedRoute>} />
      <Route path="/cases/new" element={<ProtectedRoute><NewCasePage /></ProtectedRoute>} />
      <Route path="/cases/:caseId" element={<ProtectedRoute><CaseDetailPage /></ProtectedRoute>} />
      <Route path="/evidence" element={<ProtectedRoute><EvidencePage /></ProtectedRoute>} />
      <Route path="/ai-attorney" element={<ProtectedRoute><AIAttorneyPage /></ProtectedRoute>} />
      <Route path="/analyze" element={<ProtectedRoute><DocumentAnalysisPage /></ProtectedRoute>} />
      <Route path="/community" element={<ProtectedRoute><CommunityVaultPage /></ProtectedRoute>} />
      <Route path="/policy" element={<ProtectedRoute><PolicyDashboardPage /></ProtectedRoute>} />
      <Route path="/analytics" element={<ProtectedRoute><EncounterAnalytics /></ProtectedRoute>} />
      <Route path="/sos" element={<ProtectedRoute><SOSPage /></ProtectedRoute>} />
      <Route path="/attorneys" element={<ProtectedRoute><AttorneysPage /></ProtectedRoute>} />
      <Route path="/messages" element={<ProtectedRoute><MessagesPage /></ProtectedRoute>} />
      <Route path="/rights" element={<ProtectedRoute><KnowYourRightsPage /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
      <Route path="/attorney-dashboard" element={<ProtectedRoute><AttorneyDashboardPage /></ProtectedRoute>} />
      <Route path="/attorney/encounter/:encounterId" element={<ProtectedRoute><AttorneyEncounterWorkspacePage /></ProtectedRoute>} />
      <Route path="/call/:callId" element={<ProtectedRoute><VideoCallPage /></ProtectedRoute>} />
      <Route path="/recordings" element={<ProtectedRoute><RecordingsPage /></ProtectedRoute>} />
      <Route path="/scheduled-reports" element={<ProtectedRoute><ScheduledReportsPage /></ProtectedRoute>} />
      <Route path="/report-templates" element={<ProtectedRoute><ReportTemplatesPage /></ProtectedRoute>} />
      <Route path="/notification-preferences" element={<ProtectedRoute><NotificationPreferencesPage /></ProtectedRoute>} />
      <Route path="/advanced-features" element={<ProtectedRoute><AdvancedFeaturesPage /></ProtectedRoute>} />
      <Route path="/emergency-contacts" element={<ProtectedRoute><EmergencyContactsPage /></ProtectedRoute>} />
      
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
          <Toaster position="top-right" richColors />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
