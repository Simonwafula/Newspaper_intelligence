
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import EditionsLibrary from './pages/EditionsLibrary';
import EditionDetail from './pages/EditionDetail';
import Search from './pages/Search';
import GlobalSearch from './pages/GlobalSearch';
import SavedSearches from './pages/SavedSearches';
import ErrorPage from './pages/ErrorPage';
import './App.css';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="App">
          <header className="App-header">
            <h1>Newspaper PDF Intelligence</h1>
            <nav className="App-nav">
              <Link to="/" className="nav-link">Editions</Link>
              <Link to="/search" className="nav-link">Search</Link>
              <Link to="/global-search" className="nav-link">Global Search</Link>
              <Link to="/saved-searches" className="nav-link">Saved Searches</Link>
            </nav>
          </header>
          <main className="App-main">
            <Routes>
              <Route path="/" element={<EditionsLibrary />} />
              <Route path="/edition/:id" element={<EditionDetail />} />
              <Route path="/search" element={<Search />} />
              <Route path="/global-search" element={<GlobalSearch />} />
              <Route path="/saved-searches" element={<SavedSearches />} />
              <Route path="*" element={<ErrorPage />} />
            </Routes>
          </main>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;