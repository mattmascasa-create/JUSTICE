import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../../lib/utils';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { Button } from '../ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '../ui/avatar';
import { 
  LayoutDashboard, 
  FolderOpen, 
  FileBox, 
  Bot, 
  Siren, 
  Scale, 
  BookOpen, 
  Settings,
  LogOut,
  Menu,
  X,
  Moon,
  Sun,
  Shield,
  MessageCircle,
  Building,
  Map,
  Brain,
  Radio,
  Database,
  Megaphone
} from 'lucide-react';

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
  { icon: Radio, label: 'Encounter Mode', path: '/encounter', highlight: true },
  { icon: FolderOpen, label: 'My Cases', path: '/cases' },
  { icon: FileBox, label: 'Evidence', path: '/evidence' },
  { icon: Brain, label: 'Document Analysis', path: '/analyze' },
  { icon: Database, label: 'Community Vault', path: '/community', highlight: true },
  { icon: Megaphone, label: 'Policy Impact', path: '/policy', highlight: true },
  { icon: Bot, label: 'AI Attorney', path: '/ai-attorney' },
  { icon: Siren, label: 'Emergency SOS', path: '/sos', emergency: true },
  { icon: Scale, label: 'Find Attorney', path: '/attorneys' },
  { icon: MessageCircle, label: 'Messages', path: '/messages' },
  { icon: Map, label: 'Incident Map', path: '/incident-map' },
  { icon: BookOpen, label: 'Know Your Rights', path: '/rights' },
  { icon: Building, label: 'Transparency', path: '/transparency' },
  { icon: Settings, label: 'Settings', path: '/settings' },
];

export default function Sidebar({ isMobileSheet = false }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  // If rendered inside a Sheet (mobile), show simplified content
  if (isMobileSheet) {
    return (
      <div className="flex flex-col h-full pt-8">
        {/* Logo */}
        <div className="flex items-center gap-3 p-6 border-b border-border">
          <Shield className="h-8 w-8 text-signal-blue flex-shrink-0" style={{ color: '#3B82F6' }} />
          <span className="font-serif text-xl font-bold tracking-tight">JUSTICE</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || 
              (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
            
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`sheet-nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200",
                  "hover:bg-accent hover:text-accent-foreground",
                  isActive && "bg-primary text-primary-foreground",
                  item.emergency && !isActive && "hover:bg-red-500/10 hover:text-red-500"
                )}
              >
                <item.icon className={cn(
                  "h-5 w-5 flex-shrink-0",
                  item.emergency && !isActive && "text-red-500"
                )} />
                <span className={cn(
                  "font-medium",
                  item.emergency && !isActive && "text-red-500"
                )}>
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>

        {/* User Section */}
        <div className="p-4 border-t border-border space-y-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleTheme}
            data-testid="sheet-theme-toggle"
            className="w-full justify-start gap-3"
          >
            {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
          </Button>

          <div className="flex items-center gap-3 p-3 rounded-lg bg-muted">
            <Avatar className="h-9 w-9">
              <AvatarImage src={user?.picture} alt={user?.name} />
              <AvatarFallback className="bg-primary text-primary-foreground">
                {user?.name?.charAt(0)?.toUpperCase() || 'U'}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            data-testid="sheet-logout-btn"
            className="w-full justify-start gap-3 text-red-500 hover:text-red-600 hover:bg-red-500/10"
          >
            <LogOut className="h-5 w-5" />
            <span>Sign Out</span>
          </Button>
        </div>
      </div>
    );
  }

  const handleLogout = async () => {
    await logout();
  };

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className={cn(
        "flex items-center gap-3 p-6 border-b border-border",
        collapsed && "justify-center p-4"
      )}>
        <Shield className="h-8 w-8 text-signal-blue flex-shrink-0" style={{ color: '#3B82F6' }} />
        {!collapsed && (
          <span className="font-serif text-xl font-bold tracking-tight">JUSTICE</span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path || 
            (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
          
          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => setMobileOpen(false)}
              data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200",
                "hover:bg-accent hover:text-accent-foreground",
                isActive && "bg-primary text-primary-foreground",
                item.emergency && !isActive && "hover:bg-red-500/10 hover:text-red-500",
                collapsed && "justify-center px-2"
              )}
            >
              <item.icon className={cn(
                "h-5 w-5 flex-shrink-0",
                item.emergency && !isActive && "text-red-500"
              )} />
              {!collapsed && (
                <span className={cn(
                  "font-medium",
                  item.emergency && !isActive && "text-red-500"
                )}>
                  {item.label}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* User Section */}
      <div className="p-4 border-t border-border space-y-3">
        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleTheme}
          data-testid="theme-toggle"
          className={cn("w-full justify-start gap-3", collapsed && "justify-center")}
        >
          {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          {!collapsed && <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>}
        </Button>

        {/* User Info */}
        <div className={cn(
          "flex items-center gap-3 p-3 rounded-lg bg-muted",
          collapsed && "justify-center p-2"
        )}>
          <Avatar className="h-9 w-9">
            <AvatarImage src={user?.picture} alt={user?.name} />
            <AvatarFallback className="bg-primary text-primary-foreground">
              {user?.name?.charAt(0)?.toUpperCase() || 'U'}
            </AvatarFallback>
          </Avatar>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
          )}
        </div>

        {/* Logout */}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleLogout}
          data-testid="logout-btn"
          className={cn("w-full justify-start gap-3 text-red-500 hover:text-red-600 hover:bg-red-500/10", collapsed && "justify-center")}
        >
          <LogOut className="h-5 w-5" />
          {!collapsed && <span>Sign Out</span>}
        </Button>
      </div>

      {/* Collapse Toggle (Desktop) */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setCollapsed(!collapsed)}
        className="hidden lg:flex absolute -right-3 top-20 h-6 w-6 rounded-full border border-border bg-background p-0"
        data-testid="sidebar-collapse"
      >
        <Menu className="h-3 w-3" />
      </Button>
    </div>
  );

  return (
    <>
      {/* Mobile Menu Button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setMobileOpen(true)}
        className="fixed top-4 left-4 z-50 lg:hidden"
        data-testid="mobile-menu-btn"
      >
        <Menu className="h-6 w-6" />
      </Button>

      {/* Mobile Overlay */}
      {mobileOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile Sidebar */}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-50 w-72 bg-card border-r border-border transform transition-transform duration-300 lg:hidden",
        mobileOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setMobileOpen(false)}
          className="absolute top-4 right-4"
        >
          <X className="h-5 w-5" />
        </Button>
        <SidebarContent />
      </aside>

      {/* Desktop Sidebar */}
      <aside className={cn(
        "hidden lg:flex flex-col fixed inset-y-0 left-0 z-30 bg-card border-r border-border transition-all duration-300",
        collapsed ? "w-20" : "w-72"
      )}>
        <SidebarContent />
      </aside>

      {/* Spacer for main content */}
      <div className={cn(
        "hidden lg:block flex-shrink-0 transition-all duration-300",
        collapsed ? "w-20" : "w-72"
      )} />
    </>
  );
}
