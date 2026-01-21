import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import EditionsLibrary from './pages/EditionsLibrary';
import EditionDetail from './pages/EditionDetail';
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
          </header>
          <main className="App-main">
            <Routes>
              <Route path="/" element={<EditionsLibrary />} />
              <Route path="/edition/:id" element={<EditionDetail />} />
            </Routes>
          </main>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;