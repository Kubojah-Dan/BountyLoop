import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { LiveFeed } from './pages/LiveFeed';
import { ReviewQueue } from './pages/ReviewQueue';
import { MapPage } from './pages/MapPage';
import { Impact } from './pages/Impact';
import { Recipients } from './pages/Recipients';
import { Settings } from './pages/Settings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen flex flex-col bg-slate-50 text-slate-800">
          <Navbar />
          <div className="flex flex-1">
            <Sidebar />
            <main className="flex-1 overflow-y-auto">
              <Routes>
                <Route path="/" element={<LiveFeed />} />
                <Route path="/review-queue" element={<ReviewQueue />} />
                <Route path="/map" element={<MapPage />} />
                <Route path="/impact" element={<Impact />} />
                <Route path="/recipients" element={<Recipients />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </main>
          </div>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;

