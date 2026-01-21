import React from 'react';
import Sidebar from './Sidebar';
import MobileNav from './MobileNav';

export default function AppLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <main className="flex-1 lg:ml-0 pb-20 lg:pb-0">
        <div className="min-h-screen p-4 lg:p-8 pt-16 lg:pt-8">
          {children}
        </div>
      </main>
      <MobileNav />
    </div>
  );
}
