import { Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PublicHeader } from './components/layout/PublicHeader';
import { AuthenticatedHeader } from './components/layout/AuthenticatedHeader';
import PublicLandingPage from './pages/PublicLandingPage';
import LoginPage from './pages/LoginPage';
import RequestAccessPage from './pages/RequestAccessPage';
import EditionsLibrary from './pages/EditionsLibrary';
import EditionDetail from './pages/EditionDetail';
import Search from './pages/Search';
import GlobalSearch from './pages/GlobalSearch';
import SavedSearches from './pages/SavedSearches';
import Admin from './pages/Admin';
import ErrorPage from './pages/ErrorPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Layout component for public pages
function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-paper-50">
      <PublicHeader />
      <main>
        {children}
      </main>
    </div>
  );
}

// Layout component for authenticated pages
function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-paper-50">
      <AuthenticatedHeader />
      <main>
        {children}
      </main>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        {/* Public routes with public layout */}
        <Route path="/" element={<PublicLayout><PublicLandingPage /></PublicLayout>} />
        <Route path="/login" element={<PublicLayout><LoginPage /></PublicLayout>} />
        <Route path="/request-access" element={<PublicLayout><RequestAccessPage /></PublicLayout>} />
        
        {/* Authenticated app routes with authenticated layout */}
        <Route path="/app" element={<AuthenticatedLayout />}>
          <Route path="editions" element={<EditionsLibrary />} />
          <Route path="editions/:id" element={<EditionDetail />} />
          <Route path="search" element={<Search />} />
          <Route path="global-search" element={<GlobalSearch />} />
          <Route path="saved-searches" element={<SavedSearches />} />
          <Route path="admin" element={<Admin />} />
        </Route>
        
        {/* Redirect old routes */}
        <Route path="/edition/:id" element={<Navigate to="/app/editions/:id" replace />} />
        <Route path="/search" element={<Navigate to="/app/search" replace />} />
        <Route path="/global-search" element={<Navigate to="/app/global-search" replace />} />
        <Route path="/saved-searches" element={<Navigate to="/app/saved-searches" replace />} />
        <Route path="/admin" element={<Navigate to="/app/admin" replace />} />
        
        <Route path="*" element={<ErrorPage />} />
      </Routes>
    </QueryClientProvider>
  );
}

export default App;