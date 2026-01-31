import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

// Register Service Worker for PWA functionality
const registerServiceWorker = async () => {
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.register('/service-worker.js', {
        scope: '/'
      });
      
      console.log('JUSTICE PWA: Service Worker registered successfully');
      
      // Check for updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New content available, prompt user to refresh
              console.log('JUSTICE PWA: New version available');
            }
          });
        }
      });
      
      return registration;
    } catch (error) {
      console.error('JUSTICE PWA: Service Worker registration failed:', error);
    }
  }
};

// Register on load
if (typeof window !== 'undefined') {
  window.addEventListener('load', registerServiceWorker);
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
