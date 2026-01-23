import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { searchApi } from '../services/api';
import { SearchResult, ItemType, ItemSubtype } from '../types';
import { PageContainer, PageHeader } from '../components/layout';
import { Button, Input, Card, Loading } from '../components/ui';

const Search = () => {
  const [query, setQuery] = useState('');
  const [searchScope, setSearchScope] = useState<'all' | 'edition'>('all');
  const [editionId, setEditionId] = useState('');
  const [filters, setFilters] = useState({
    item_type: '' as ItemType | '',
    subtype: '' as ItemSubtype | '',
    newspaper_name: '',
    page_number: '',
  });

  const { data: results, isLoading, error, refetch } = useQuery({
    queryKey: ['search', query, searchScope, editionId, filters],
    queryFn: () => {
      if (!query.trim()) return [];

      const searchFilters: Record<string, string | number> = {};
      if (filters.item_type) searchFilters.item_type = filters.item_type;
      if (filters.subtype) searchFilters.subtype = filters.subtype;

      if (searchScope === 'all') {
        if (filters.newspaper_name) searchFilters.newspaper_name = filters.newspaper_name;
        return searchApi.searchAll(query, searchFilters);
      } else {
        if (filters.page_number) searchFilters.page_number = parseInt(filters.page_number);
        return searchApi.searchEdition(parseInt(editionId), query, searchFilters);
      }
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

  return (
    <PageContainer maxWidth="4xl">
      <PageHeader
        title="Search"
        description="Search within newspaper editions"
      />

      {/* Search Form */}
      <Card className="mb-8">
        <form onSubmit={handleSearch} className="p-6 space-y-4">
          {/* Search Input */}
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

          {/* Search Scope */}
          <div className="flex flex-wrap items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                value="all"
                checked={searchScope === 'all'}
                onChange={(e) => setSearchScope(e.target.value as 'all' | 'edition')}
                className="w-4 h-4 text-ink-800 focus:ring-ink-800"
              />
              <span className="text-sm text-ink-800">Search All Editions</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                value="edition"
                checked={searchScope === 'edition'}
                onChange={(e) => setSearchScope(e.target.value as 'all' | 'edition')}
                className="w-4 h-4 text-ink-800 focus:ring-ink-800"
              />
              <span className="text-sm text-ink-800">Search Specific Edition</span>
            </label>
            {searchScope === 'edition' && (
              <input
                type="number"
                value={editionId}
                onChange={(e) => setEditionId(e.target.value)}
                placeholder="Edition ID"
                className="w-32 px-3 py-1.5 bg-white border border-stone-300 rounded-lg text-sm text-ink-800 focus:outline-none focus:ring-2 focus:ring-ink-800"
                required
              />
            )}
          </div>

          {/* Filters */}
          <div className="pt-4 border-t border-stone-200 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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

            {searchScope === 'all' && (
              <Input
                label="Newspaper"
                type="text"
                value={filters.newspaper_name}
                onChange={(e) => handleFilterChange('newspaper_name', e.target.value)}
                placeholder="Newspaper name"
              />
            )}

            {searchScope === 'edition' && (
              <Input
                label="Page Number"
                type="number"
                value={filters.page_number}
                onChange={(e) => handleFilterChange('page_number', e.target.value)}
                placeholder="Page number"
                min={1}
              />
            )}
          </div>
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
                No results found for your search.
              </div>
            </Card>
          ) : (
            <div className="space-y-4">
              {results.map((result: SearchResult) => (
                <Card key={result.item_id} hover>
                  <Link
                    to={`/item/${result.item_id}`}
                    className="text-lg font-semibold text-ink-800 hover:text-ink-700 block mb-2"
                  >
                    {result.title || 'Untitled'}
                  </Link>

                  <p className="text-stone-600 text-sm leading-relaxed mb-2">
                    {highlightText(result.snippet, result.highlights)}
                  </p>

                  <div className="text-sm text-stone-500">
                    Page {result.page_number}
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

export default Search;
