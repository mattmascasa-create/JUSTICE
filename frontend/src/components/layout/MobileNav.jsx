import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../../lib/utils';
import { LayoutDashboard, FolderOpen, Bot, Siren, Menu } from 'lucide-react';
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from '../ui/sheet';
import { VisuallyHidden } from '@radix-ui/react-visually-hidden';
import Sidebar from './Sidebar';

const mobileNavItems = [
  { icon: LayoutDashboard, label: 'Home', path: '/dashboard' },
  { icon: FolderOpen, label: 'Cases', path: '/cases' },
  { icon: Siren, label: 'SOS', path: '/sos', emergency: true },
  { icon: Bot, label: 'AI Help', path: '/ai-attorney' },
];

export default function MobileNav() {
  const location = useLocation();

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 lg:hidden bg-background border-t border-border safe-area-inset-bottom">
      <nav className="flex items-center justify-around h-16 px-2">
        {mobileNavItems.map((item) => {
          const isActive = location.pathname === item.path || 
            (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
          
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex flex-col items-center justify-center flex-1 h-full gap-1 transition-colors",
                isActive ? "text-primary" : "text-muted-foreground",
                item.emergency && !isActive && "text-red-500"
              )}
              data-testid={`mobile-nav-${item.label.toLowerCase()}`}
            >
              <div className={cn(
                "p-1.5 rounded-lg transition-colors",
                isActive && "bg-primary/10",
                item.emergency && "bg-red-500/10"
              )}>
                <item.icon className={cn(
                  "h-5 w-5",
                  item.emergency && "animate-pulse"
                )} />
              </div>
              <span className="text-[10px] font-medium">{item.label}</span>
            </Link>
          );
        })}
        
        {/* More menu */}
        <Sheet>
          <SheetTrigger asChild>
            <button className="flex flex-col items-center justify-center flex-1 h-full gap-1 text-muted-foreground">
              <div className="p-1.5 rounded-lg">
                <Menu className="h-5 w-5" />
              </div>
              <span className="text-[10px] font-medium">More</span>
            </button>
          </SheetTrigger>
          <SheetContent side="right" className="w-72 p-0">
            <Sidebar isMobileSheet />
          </SheetContent>
        </Sheet>
      </nav>
    </div>
  );
}
