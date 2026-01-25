import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { searchApi } from '../services/api';
import { GlobalSearchResult, ItemType, ItemSubtype } from '../types';
import { PageContainer, PageHeader } from '../components/layout';
import { Button, Input, Card, ItemTypeBadge, Loading } from '../components/ui';

const GlobalSearch = () => {
  const [query, setQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    item_type: '' as ItemType | '',
    subtype: '' as ItemSubtype | '',
    newspaper_name: '',
    date_from: '',
    date_to: '',
  });

  const { data: results, isLoading, error, refetch } = useQuery({
    queryKey: ['global-search', query, filters],
    queryFn: () => {
      if (!query.trim()) return [];

      const searchFilters: Record<string, string | number> = {};
      if (filters.item_type) searchFilters.item_type = filters.item_type;
      if (filters.subtype) searchFilters.subtype = filters.subtype;
      if (filters.newspaper_name) searchFilters.newspaper_name = filters.newspaper_name;
      if (filters.date_from) searchFilters.date_from = filters.date_from;
      if (filters.date_to) searchFilters.date_to = filters.date_to;

      return searchApi.searchAll(query, searchFilters);
    },
    enabled: false,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      refetch();
    }
  };

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const highlightText = (text: string, highlights: string[]) => {
    if (!highlights.length) return text;

    let highlightedText = text;
    highlights.forEach(term => {
      const regex = new RegExp(`(${term})`, 'gi');
      highlightedText = highlightedText.replace(regex, '<mark class="bg-yellow-200 px-0.5 rounded">$1</mark>');
    });

    return <span dangerouslySetInnerHTML={{ __html: highlightedText }} />;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <PageContainer maxWidth="4xl">
      <PageHeader
        title="Global Search"
        description="Search across all newspaper editions in the archive"
      />

      {/* Search Form */}
      <Card className="mb-8">
        <form onSubmit={handleSearch} className="p-6">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <Input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter search terms..."
                required
              />
            </div>
            <Button type="submit" isLoading={isLoading}>
              {isLoading ? 'Searching...' : 'Search'}
            </Button>
          </div>

          {/* Filters Toggle */}
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className="mt-4 text-sm text-ink-700 hover:text-ink-800 flex items-center gap-1"
          >
            <svg
              className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
            {showFilters ? 'Hide Filters' : 'Show Filters'}
          </button>

          {/* Filters */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t border-stone-200 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <div>
                <label className="block text-sm font-medium text-ink-800 mb-1.5">Type</label>
                <select
                  value={filters.item_type}
                  onChange={(e) => handleFilterChange('item_type', e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-stone-300 rounded-lg text-ink-800 focus:outline-none focus:ring-2 focus:ring-ink-800"
                >
                  <option value="">All Types</option>
                  <option value="STORY">Stories</option>
                  <option value="AD">Advertisements</option>
                  <option value="CLASSIFIED">Classifieds</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-ink-800 mb-1.5">Subtype</label>
                <select
                  value={filters.subtype}
                  onChange={(e) => handleFilterChange('subtype', e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-stone-300 rounded-lg text-ink-800 focus:outline-none focus:ring-2 focus:ring-ink-800 disabled:bg-stone-100"
                  disabled={!filters.item_type}
                >
                  <option value="">All Subtypes</option>
                  {filters.item_type === 'CLASSIFIED' && (
                    <>
                      <option value="TENDER">Tenders</option>
                      <option value="JOB">Jobs</option>
                      <option value="AUCTION">Auctions</option>
                      <option value="NOTICE">Notices</option>
                      <option value="PROPERTY">Property</option>
                      <option value="OTHER">Other</option>
                    </>
                  )}
                </select>
              </div>

              <Input
                label="Newspaper"
                type="text"
                value={filters.newspaper_name}
                onChange={(e) => handleFilterChange('newspaper_name', e.target.value)}
                placeholder="Newspaper name"
              />

              <Input
                label="From Date"
                type="date"
                value={filters.date_from}
                onChange={(e) => handleFilterChange('date_from', e.target.value)}
              />

              <Input
                label="To Date"
                type="date"
                value={filters.date_to}
                onChange={(e) => handleFilterChange('date_to', e.target.value)}
              />
            </div>
          )}
        </form>
      </Card>

      {/* Error State */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          Search error: {(error as Error).message}
        </div>
      )}

      {/* Loading State */}
      {isLoading && <Loading message="Searching..." />}

      {/* Results */}
      {results && !isLoading && (
        <div>
          <h2 className="text-xl font-semibold text-ink-800 mb-4">
            {results.length} result{results.length !== 1 ? 's' : ''} found
          </h2>

          {results.length === 0 ? (
            <Card>
              <div className="p-8 text-center text-stone-500">
                No results found for your search. Try different keywords or filters.
              </div>
            </Card>
          ) : (
            <div className="space-y-4">
              {results.map((result: GlobalSearchResult) => (
                <Card key={result.item_id} hover>
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 mb-2">
                    <Link
                      to={`/app/editions/${result.edition_id}`}
                      className="text-lg font-semibold text-ink-800 hover:text-ink-700"
                    >
                      {result.title || 'Untitled'}
                    </Link>
                    <div className="flex items-center gap-2">
                      <ItemTypeBadge type={result.item_type} />
                      {result.subtype && (
                        <span className="text-xs text-stone-500">{result.subtype}</span>
                      )}
                    </div>
                  </div>

                  <p className="text-stone-600 text-sm leading-relaxed mb-3">
                    {highlightText(result.snippet, result.highlights)}
                  </p>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-stone-500">
                    <span className="font-medium text-ink-800">{result.newspaper_name}</span>
                    <span>{formatDate(result.edition_date)}</span>
                    <span>Page {result.page_number}</span>
                    <Link
                      to={`/app/editions/${result.edition_id}`}
                      className="text-ink-700 hover:text-ink-800 hover:underline"
                    >
                      View Edition
                    </Link>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </PageContainer>
  );
};

export default GlobalSearch;
