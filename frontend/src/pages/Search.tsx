import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { searchApi } from '../services/api';
import { SearchResult, ItemType, ItemSubtype } from '../types';

const Search: React.FC = () => {
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
      
      const searchFilters: any = {};
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
    enabled: false, // Don't auto-search until user clicks search
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
      highlightedText = highlightedText.replace(regex, '<mark>$1</mark>');
    });
    
    return <span dangerouslySetInnerHTML={{ __html: highlightedText }} />;
  };

  return (
    <div className="search-container">
      <h1>Search Newspaper Archive</h1>
      
      <form onSubmit={handleSearch} className="search-form">
        <div className="search-input-group">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter search terms..."
            className="search-input"
            required
          />
          <button type="submit" className="btn" disabled={isLoading}>
            {isLoading ? 'Searching...' : 'Search'}
          </button>
        </div>
        
        <div className="search-scope">
          <label>
            <input
              type="radio"
              value="all"
              checked={searchScope === 'all'}
              onChange={(e) => setSearchScope(e.target.value as 'all' | 'edition')}
            />
            Search All Editions
          </label>
          <label>
            <input
              type="radio"
              value="edition"
              checked={searchScope === 'edition'}
              onChange={(e) => setSearchScope(e.target.value as 'all' | 'edition')}
            />
            Search Specific Edition
          </label>
          {searchScope === 'edition' && (
            <input
              type="number"
              value={editionId}
              onChange={(e) => setEditionId(e.target.value)}
              placeholder="Edition ID"
              className="edition-id-input"
              required
            />
          )}
        </div>
        
        <div className="search-filters">
          <select
            value={filters.item_type}
            onChange={(e) => handleFilterChange('item_type', e.target.value)}
            className="filter-select"
          >
            <option value="">All Types</option>
            <option value="STORY">Stories</option>
            <option value="AD">Advertisements</option>
            <option value="CLASSIFIED">Classifieds</option>
          </select>
          
          <select
            value={filters.subtype}
            onChange={(e) => handleFilterChange('subtype', e.target.value)}
            className="filter-select"
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
          
          {searchScope === 'all' && (
            <input
              type="text"
              value={filters.newspaper_name}
              onChange={(e) => handleFilterChange('newspaper_name', e.target.value)}
              placeholder="Newspaper name"
              className="filter-input"
            />
          )}
          
          {searchScope === 'edition' && (
            <input
              type="number"
              value={filters.page_number}
              onChange={(e) => handleFilterChange('page_number', e.target.value)}
              placeholder="Page number"
              className="filter-input"
              min="1"
            />
          )}
        </div>
      </form>

      {error && (
        <div className="error">
          Search error: {(error as Error).message}
        </div>
      )}

      {results && (
        <div className="search-results">
          <h2>Search Results ({results.length})</h2>
          {results.length === 0 ? (
            <p>No results found for your search.</p>
          ) : (
            <div className="search-results-list">
              {results.map((result: SearchResult) => (
                <div key={result.item_id} className="search-result-item">
                  <div className="search-result-title">
                    <Link to={`/item/${result.item_id}`}>
                      {result.title || 'Untitled'}
                    </Link>
                  </div>
                  <div className="search-result-snippet">
                    {highlightText(result.snippet, result.highlights)}
                  </div>
                  <div className="search-result-meta">
                    Page {result.page_number}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Search;