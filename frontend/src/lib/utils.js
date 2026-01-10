import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatDate(date) {
  if (!date) return '';
  const d = new Date(date);
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

export function formatDateTime(date) {
  if (!date) return '';
  const d = new Date(date);
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function getInitials(name) {
  if (!name) return 'U';
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
}

export function getSeverityColor(severity) {
  switch (severity?.toLowerCase()) {
    case 'critical':
      return 'bg-red-500/10 text-red-500 border-red-500/20';
    case 'high':
      return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
    case 'medium':
      return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
    case 'low':
      return 'bg-green-500/10 text-green-500 border-green-500/20';
    default:
      return 'bg-muted text-muted-foreground';
  }
}

export function getStatusColor(status) {
  switch (status?.toLowerCase()) {
    case 'open':
      return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    case 'in_progress':
    case 'under_review':
      return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
    case 'resolved':
      return 'bg-green-500/10 text-green-500 border-green-500/20';
    case 'closed':
      return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    default:
      return 'bg-muted text-muted-foreground';
  }
}
