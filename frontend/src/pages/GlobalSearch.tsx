import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { searchApi } from '../services/api';
import { GlobalSearchResult, ItemType, ItemSubtype } from '../types';

const GlobalSearch: React.FC = () => {
  const [query, setQuery] = useState('');
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getItemTypeColor = (itemType: ItemType) => {
    switch (itemType) {
      case 'STORY': return '#2563eb';
      case 'AD': return '#dc2626';
      case 'CLASSIFIED': return '#16a34a';
      default: return '#6b7280';
    }
  };

  return (
    <div className="global-search-container">
      <h1>Global Newspaper Search</h1>
      <p>Search across all newspaper editions in the archive</p>
      
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
          
          <input
            type="text"
            value={filters.newspaper_name}
            onChange={(e) => handleFilterChange('newspaper_name', e.target.value)}
            placeholder="Newspaper name"
            className="filter-input"
          />
          
          <input
            type="date"
            value={filters.date_from}
            onChange={(e) => handleFilterChange('date_from', e.target.value)}
            placeholder="From date"
            className="filter-input"
          />
          
          <input
            type="date"
            value={filters.date_to}
            onChange={(e) => handleFilterChange('date_to', e.target.value)}
            placeholder="To date"
            className="filter-input"
          />
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
              {results.map((result: GlobalSearchResult) => (
                <div key={result.item_id} className="search-result-item">
                  <div className="search-result-header">
                    <div className="search-result-title">
                      <Link to={`/edition/${result.edition_id}/item/${result.item_id}`}>
                        {result.title || 'Untitled'}
                      </Link>
                    </div>
                    <div 
                      className="item-type-badge"
                      style={{ backgroundColor: getItemTypeColor(result.item_type) }}
                    >
                      {result.item_type}
                      {result.subtype && ` - ${result.subtype}`}
                    </div>
                  </div>
                  
                  <div className="search-result-snippet">
                    {highlightText(result.snippet, result.highlights)}
                  </div>
                  
                  <div className="search-result-meta">
                    <span className="meta-item">
                      <strong>{result.newspaper_name}</strong>
                    </span>
                    <span className="meta-item">
                      {formatDate(result.edition_date)}
                    </span>
                    <span className="meta-item">
                      Page {result.page_number}
                    </span>
                    <span className="meta-item">
                      <Link to={`/edition/${result.edition_id}`}>
                        View Edition
                      </Link>
                    </span>
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

export default GlobalSearch;