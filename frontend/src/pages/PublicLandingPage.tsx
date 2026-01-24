import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

interface Edition {
  id: number;
  newspaper_name: string;
  edition_date: string;
  status?: string;
  cover_image_url?: string;
}

export default function PublicLandingPage() {
  const [editions, setEditions] = useState<Edition[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const fetchEditions = async () => {
      try {
        const response = await fetch('/api/public/editions');
        if (!response.ok) {
          throw new Error('Failed to fetch editions');
        }
        const data = await response.json();
        setEditions(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchEditions();
  }, []);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-stone-50 flex justify-center items-center">
        <div className="text-ink-600">Loading editions...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-stone-50 flex justify-center items-center">
        <div className="text-red-600">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-50">
      {/* Hero Section */}
      <div className="bg-white border-b border-stone-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center">
            <h1 className="font-serif text-4xl font-bold text-ink-800">
              Newspaper Intelligence
            </h1>
            <p className="mt-4 text-xl text-ink-600 max-w-3xl mx-auto">
              Turn newspaper PDFs into searchable, structured intelligence.
            </p>
            <div className="mt-8 flex justify-center space-x-4">
              <Link
                to="/login"
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-ink-800 hover:bg-ink-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ink-500"
              >
                Sign in
              </Link>
              <Link
                to="/request-access"
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-ink-800 bg-ink-100 hover:bg-ink-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ink-500"
              >
                Request Access
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Cover Gallery */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-ink-900">
            Newspaper Editions
          </h2>
          <p className="mt-4 text-lg text-ink-600">
            Browse recent newspaper covers. Sign in to read stories, search, and track opportunities.
          </p>
        </div>

        {editions.length === 0 ? (
          <div className="mt-12 text-center">
            <p className="text-ink-500">No editions available yet.</p>
          </div>
        ) : (
          <div className="mt-12 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {editions.map((edition) => (
              <div
                key={edition.id}
                className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-300"
              >
                <div className="aspect-w-3 aspect-h-4 bg-stone-200">
                  {edition.cover_image_url ? (
                    <img
                      src={edition.cover_image_url}
                      alt={`${edition.newspaper_name} cover`}
                      className="w-full h-48 object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-48 bg-stone-300 flex items-center justify-center">
                      <div className="text-center">
                        <div className="text-2xl font-serif text-stone-600 mb-2">
                          {edition.newspaper_name}
                        </div>
                        <div className="text-sm text-stone-500">
                          {formatDate(edition.edition_date)}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                
                <div className="p-4">
                  <h3 className="text-lg font-medium text-ink-900 mb-2">
                    {edition.newspaper_name}
                  </h3>
                  <p className="text-sm text-ink-600 mb-4">
                    {formatDate(edition.edition_date)}
                  </p>
                  {edition.status && (
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      edition.status === 'READY' || edition.status === 'ARCHIVED'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {edition.status}
                    </span>
                  )}
                </div>

                <div className="px-4 pb-4">
                  <Link
                    to={`/login`}
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-ink-800 bg-ink-100 hover:bg-ink-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ink-500"
                  >
                    Sign in to read
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-16 text-center">
          <h3 className="text-2xl font-bold text-ink-900 mb-4">
            Want to read full stories and search?
          </h3>
          <p className="text-lg text-ink-600 mb-8">
            Sign in to access full newspaper content, search across editions, and save custom searches.
          </p>
          <div className="flex justify-center space-x-4">
            <Link
              to="/login"
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-ink-800 hover:bg-ink-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ink-500"
            >
              Sign In
            </Link>
            <Link
              to="/request-access"
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-ink-800 bg-ink-100 hover:bg-ink-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ink-500"
            >
              Request Access
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
