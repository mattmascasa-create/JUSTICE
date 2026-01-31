import React from 'react';
import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import MobileNav from './MobileNav';
import { FloatingGuidanceButton } from '../SmartGuidancePanel';

export default function AppLayout({ children }) {
  const location = useLocation();
  const currentPage = location.pathname.replace('/', '') || 'dashboard';
  
  // Don't show floating button on encounter page (it has its own guidance)
  const showFloatingGuide = !location.pathname.includes('/encounter');
  
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <main className="flex-1 lg:ml-0 pb-20 lg:pb-0">
        <div className="min-h-screen p-4 lg:p-8 pt-16 lg:pt-8">
          {children}
        </div>
      </main>
      <MobileNav />
      {showFloatingGuide && <FloatingGuidanceButton currentPage={currentPage} />}
    </div>
  );
}
