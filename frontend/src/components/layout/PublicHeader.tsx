import { Link } from 'react-router-dom';

export function PublicHeader() {
  return (
    <header className="bg-white border-b border-stone-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2">
            <span className="font-serif text-xl font-bold text-ink-800">
              Newspaper Intelligence
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-4">
            <Link
              to="/login"
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150 text-ink-700 hover:bg-stone-100"
            >
              Login
            </Link>
            <Link
              to="/request-access"
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150 text-ink-800 bg-ink-100 hover:bg-ink-200"
            >
              Request Access
            </Link>
          </nav>

          {/* Mobile Menu Button */}
          <div className="md:hidden">
            <Link
              to="/login"
              className="px-4 py-2 rounded-lg text-sm font-medium text-ink-800 bg-ink-100 hover:bg-ink-200"
            >
              Login
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}