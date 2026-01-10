import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { ThemeProvider } from "./contexts/ThemeContext";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
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
import SettingsPage from "./pages/SettingsPage";

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

  return children;
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
      
      {/* Protected Routes */}
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/cases" element={<ProtectedRoute><CasesPage /></ProtectedRoute>} />
      <Route path="/cases/new" element={<ProtectedRoute><NewCasePage /></ProtectedRoute>} />
      <Route path="/cases/:caseId" element={<ProtectedRoute><CaseDetailPage /></ProtectedRoute>} />
      <Route path="/evidence" element={<ProtectedRoute><EvidencePage /></ProtectedRoute>} />
      <Route path="/ai-attorney" element={<ProtectedRoute><AIAttorneyPage /></ProtectedRoute>} />
      <Route path="/sos" element={<ProtectedRoute><SOSPage /></ProtectedRoute>} />
      <Route path="/attorneys" element={<ProtectedRoute><AttorneysPage /></ProtectedRoute>} />
      <Route path="/rights" element={<ProtectedRoute><KnowYourRightsPage /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
      
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
          <Toaster position="top-right" richColors />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
