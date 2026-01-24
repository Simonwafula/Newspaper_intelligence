import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

interface NavItem {
  path: string;
  label: string;
  requireAdmin?: boolean;
}

export function AuthenticatedHeader() {
  const { role, logout, isAdmin } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const isActive = (path: string) => {
    return location.pathname.startsWith(path);
  };

  const readerNavItems: NavItem[] = [
    { path: '/app/editions', label: 'Editions' },
    { path: '/app/search', label: 'Search' },
    { path: '/app/global-search', label: 'Global Search' },
    { path: '/app/favorites', label: 'Favorites' },
    { path: '/app/collections', label: 'Collections' },
    { path: '/app/trends', label: 'Trends' },
    { path: '/app/saved-searches', label: 'Saved Searches' },
  ];

  const adminNavItems: NavItem[] = [
    { path: '/app/categories', label: 'Categories', requireAdmin: true },
  ];

  const allNavItems = [...readerNavItems, ...adminNavItems];

  const filteredNavItems = isAdmin()
    ? allNavItems
    : readerNavItems;

  return (
    <header className="bg-white border-b border-stone-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/app/editions" className="flex items-center space-x-2">
            <span className="font-serif text-xl font-bold text-ink-800">
              Newspaper Intelligence
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-1">
            {filteredNavItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`
                  px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150
                  ${isActive(item.path)
                    ? 'bg-ink-800 text-white'
                    : 'text-ink-700 hover:bg-stone-100'
                  }
                  ${item.requireAdmin ? 'font-bold' : ''}
                `}
              >
                {item.label}
              </Link>
            ))}
            <div className="ml-4 flex items-center space-x-2">
              <span className="text-sm text-ink-600">
                {role === 'ADMIN' ? 'Admin' : 'Reader'}
              </span>
              <button
                onClick={handleLogout}
                className="px-3 py-1 text-sm text-red-600 hover:text-red-800 border border-red-300 rounded hover:bg-red-50"
              >
                Logout
              </button>
            </div>
          </nav>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 rounded-lg text-ink-700 hover:bg-stone-100"
            aria-label="Toggle menu"
          >
            {isMobileMenuOpen ? (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isMobileMenuOpen && (
          <nav className="md:hidden py-4 border-t border-stone-200">
            <div className="flex flex-col space-y-1">
              {filteredNavItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`
                    px-4 py-3 rounded-lg text-sm font-medium transition-colors duration-150
                    ${isActive(item.path)
                      ? 'bg-ink-800 text-white'
                      : 'text-ink-700 hover:bg-stone-100'
                    }
                    ${item.requireAdmin ? 'font-bold' : ''}
                  `}
                >
                  {item.label}
                </Link>
              ))}
              <div className="pt-4 border-t border-stone-200 mt-4">
                <div className="px-4 py-2 text-sm text-ink-600">
                  Logged in as: {role === 'ADMIN' ? 'Admin' : 'Reader'}
                </div>
                <button
                  onClick={handleLogout}
                  className="mx-4 px-4 py-2 text-sm text-red-600 hover:text-red-800 border border-red-300 rounded hover:bg-red-50"
                >
                  Logout
                </button>
              </div>
            </div>
          </nav>
        )}
      </div>
    </header>
  );
}