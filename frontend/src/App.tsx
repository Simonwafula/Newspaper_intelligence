
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import EditionsLibrary from './pages/EditionsLibrary';
import EditionDetail from './pages/EditionDetail';
import Search from './pages/Search';
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
            </nav>
          </header>
          <main className="App-main">
            <Routes>
              <Route path="/" element={<EditionsLibrary />} />
              <Route path="/edition/:id" element={<EditionDetail />} />
              <Route path="/search" element={<Search />} />
            </Routes>
          </main>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;