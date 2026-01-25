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
  Megaphone,
  BarChart3,
  Briefcase,
  Video,
  CalendarClock,
  Palette,
  Zap,
  Users,
  Eye,
  Camera,
  FileText
} from 'lucide-react';
import NotificationBell from '../NotificationBell';
import ConnectionIndicator from '../ConnectionIndicator';

// Get nav items based on user role
const getNavItems = (role) => {
  const baseItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
    { icon: Radio, label: 'Encounter Mode', path: '/encounter', highlight: true },
    { icon: Zap, label: 'Advanced Features', path: '/advanced-features', highlight: true },
    { icon: BarChart3, label: 'Encounter Analytics', path: '/analytics', highlight: true },
    { icon: Scale, label: 'Court-Grade AI', path: '/court-grade-ai', highlight: true },
    { icon: BarChart3, label: 'Premium Analytics', path: '/premium-analytics', highlight: true },
    { icon: FolderOpen, label: 'My Cases', path: '/cases' },
    { icon: FileBox, label: 'Evidence', path: '/evidence' },
    { icon: Video, label: 'Recordings', path: '/recordings' },
    { icon: CalendarClock, label: 'Scheduled Reports', path: '/scheduled-reports' },
    { icon: Palette, label: 'Report Templates', path: '/report-templates' },
    { icon: Brain, label: 'Document Analysis', path: '/analyze' },
    { icon: FileText, label: 'Legal Documents', path: '/legal-documents', highlight: true },
    { icon: Database, label: 'Community Vault', path: '/community', highlight: true },
    { icon: Megaphone, label: 'Policy Impact', path: '/policy', highlight: true },
    { icon: Bot, label: 'AI Attorney', path: '/ai-attorney' },
    { icon: Siren, label: 'Emergency SOS', path: '/sos', emergency: true },
    { icon: Users, label: 'Emergency Contacts', path: '/emergency-contacts' },
    { icon: Eye, label: 'Witness Network', path: '/witness-network' },
    { icon: Camera, label: 'Hardware', path: '/hardware' },
    { icon: Scale, label: 'Find Attorney', path: '/attorneys' },
    { icon: MessageCircle, label: 'Messages', path: '/messages' },
    { icon: Map, label: 'Incident Map', path: '/incident-map' },
    { icon: BookOpen, label: 'Know Your Rights', path: '/training' },
    { icon: Building, label: 'Transparency', path: '/transparency' },
    { icon: Shield, label: 'Accountability Portal', path: '/accountability', highlight: true },
    { icon: Settings, label: 'Settings', path: '/settings' },
  ];

  // Add attorney-specific items
  if (role === 'attorney') {
    // Insert attorney dashboard after the main dashboard
    baseItems.splice(1, 0, { 
      icon: Briefcase, 
      label: 'Attorney Dashboard', 
      path: '/attorney-dashboard',
      highlight: true 
    });
  }

  return baseItems;
};

export default function Sidebar({ isMobileSheet = false }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  
  // Get nav items based on user role
  const navItems = getNavItems(user?.role);

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
        <SidebarContent 
          collapsed={collapsed}
          setCollapsed={setCollapsed}
          setMobileOpen={setMobileOpen}
          navItems={navItems}
          location={location}
          user={user}
          theme={theme}
          toggleTheme={toggleTheme}
          handleLogout={handleLogout}
        />
      </aside>

      {/* Desktop Sidebar */}
      <aside className={cn(
        "hidden lg:flex flex-col fixed inset-y-0 left-0 z-30 bg-card border-r border-border transition-all duration-300",
        collapsed ? "w-20" : "w-72"
      )}>
        <SidebarContent 
          collapsed={collapsed}
          setCollapsed={setCollapsed}
          setMobileOpen={setMobileOpen}
          navItems={navItems}
          location={location}
          user={user}
          theme={theme}
          toggleTheme={toggleTheme}
          handleLogout={handleLogout}
        />
      </aside>

      {/* Spacer for main content */}
      <div className={cn(
        "hidden lg:block flex-shrink-0 transition-all duration-300",
        collapsed ? "w-20" : "w-72"
      )} />
    </>
  );
}

// Extracted SidebarContent component to avoid re-rendering issues
function SidebarContent({ 
  collapsed, 
  setCollapsed, 
  setMobileOpen, 
  navItems, 
  location, 
  user, 
  theme, 
  toggleTheme, 
  handleLogout 
}) {
  return (
    <div className="flex flex-col h-full">
      {/* Logo and Notification */}
      <div className={cn(
        "flex items-center gap-3 p-6 border-b border-border",
        collapsed && "justify-center p-4"
      )}>
        <Shield className="h-8 w-8 text-signal-blue flex-shrink-0" style={{ color: '#3B82F6' }} />
        {!collapsed && (
          <>
            <span className="font-serif text-xl font-bold tracking-tight flex-1">JUSTICE</span>
            <ConnectionIndicator />
            <NotificationBell />
          </>
        )}
        {collapsed && (
          <div className="flex flex-col items-center gap-2">
            <ConnectionIndicator />
            <NotificationBell />
          </div>
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
                item.highlight && !isActive && "text-primary",
                collapsed && "justify-center px-2"
              )}
            >
              <item.icon className={cn(
                "h-5 w-5 flex-shrink-0",
                item.emergency && !isActive && "text-red-500",
                item.highlight && !isActive && "text-primary"
              )} />
              {!collapsed && (
                <span className={cn(
                  "font-medium truncate",
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
      <div className={cn(
        "p-4 border-t border-border space-y-3",
        collapsed && "p-2"
      )}>
        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size={collapsed ? "icon" : "sm"}
          onClick={toggleTheme}
          data-testid="theme-toggle"
          className={cn(!collapsed && "w-full justify-start gap-3")}
        >
          {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          {!collapsed && <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>}
        </Button>

        {/* User Info */}
        {user && (
          <div className={cn(
            "flex items-center gap-3 p-2 rounded-lg bg-muted/50",
            collapsed && "justify-center p-2"
          )}>
            <Avatar className="h-10 w-10">
              <AvatarImage src={user.picture} alt={user.name} />
              <AvatarFallback>
                {user.name?.charAt(0).toUpperCase() || 'U'}
              </AvatarFallback>
            </Avatar>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user.name}</p>
                <p className="text-xs text-muted-foreground truncate">{user.email}</p>
              </div>
            )}
          </div>
        )}

        {/* Logout */}
        <Button
          variant="ghost"
          size={collapsed ? "icon" : "sm"}
          onClick={handleLogout}
          data-testid="logout-btn"
          className={cn(
            "text-red-500 hover:text-red-600 hover:bg-red-500/10",
            !collapsed && "w-full justify-start gap-3"
          )}
        >
          <LogOut className="h-5 w-5" />
          {!collapsed && <span>Logout</span>}
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
}
