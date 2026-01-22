import { useState, useEffect } from 'react';
import { savedSearchesApi } from '../services/api';
import { SavedSearch, SavedSearchCreate, ItemType } from '../types';

const SavedSearches = () => {
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState<SavedSearchCreate>({
    name: '',
    description: '',
    query: '',
    item_types: [],
    date_from: '',
    date_to: '',
  });

  const loadSavedSearches = async () => {
    try {
      setLoading(true);
      const searches = await savedSearchesApi.getSavedSearches();
      setSavedSearches(searches);
      setError(null);
    } catch (err) {
      setError('Failed to load saved searches');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSavedSearches();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await savedSearchesApi.createSavedSearch(formData);
      setFormData({
        name: '',
        description: '',
        query: '',
        item_types: [],
        date_from: '',
        date_to: '',
      });
      setShowCreateForm(false);
      loadSavedSearches();
    } catch (err) {
      setError('Failed to create saved search');
    }
  };

  const handleDelete = async (id: number) => {
    if (confirm('Are you sure you want to delete this saved search?')) {
      try {
        await savedSearchesApi.deleteSavedSearch(id);
        loadSavedSearches();
      } catch (err) {
        setError('Failed to delete saved search');
      }
    }
  };

  const handleUpdateMatches = async (id: number) => {
    try {
      await savedSearchesApi.updateSearchMatches(id);
      loadSavedSearches();
    } catch (err) {
      setError('Failed to update matches');
    }
  };

  const handleUpdateAllMatches = async () => {
    try {
      await savedSearchesApi.updateAllSearchMatches();
      loadSavedSearches();
    } catch (err) {
      setError('Failed to update all matches');
    }
  };

  const handleItemTypeChange = (itemType: string) => {
    setFormData(prev => ({
      ...prev,
      item_types: prev.item_types?.includes(itemType as ItemType)
        ? prev.item_types.filter(type => type !== itemType)
        : [...(prev.item_types || []), itemType as ItemType]
    }));
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getItemTypeColor = (itemType: ItemType) => {
    switch (itemType) {
      case 'STORY': return 'bg-blue-100 text-blue-800';
      case 'AD': return 'bg-green-100 text-green-800';
      case 'CLASSIFIED': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="text-center">Loading saved searches...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Saved Searches</h1>
        <div className="space-x-2">
          <button
            onClick={handleUpdateAllMatches}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            Update All Matches
          </button>
          <button
            onClick={() => setShowCreateForm(true)}
            className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
          >
            Create Saved Search
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold mb-4">Create Saved Search</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full border rounded px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full border rounded px-3 py-2"
                  rows={3}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Search Query *</label>
                <input
                  type="text"
                  required
                  value={formData.query}
                  onChange={(e) => setFormData(prev => ({ ...prev, query: e.target.value }))}
                  className="w-full border rounded px-3 py-2"
                  placeholder="Enter search terms..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Item Types</label>
                <div className="space-x-4">
                  {(['STORY', 'AD', 'CLASSIFIED'] as const).map(type => (
                    <label key={type} className="inline-flex items-center">
                      <input
                        type="checkbox"
                        checked={formData.item_types?.includes(type) || false}
                        onChange={() => handleItemTypeChange(type)}
                        className="mr-2"
                      />
                      <span className={`px-2 py-1 rounded text-xs ${getItemTypeColor(type)}`}>
                        {type}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Date From</label>
                  <input
                    type="date"
                    value={formData.date_from}
                    onChange={(e) => setFormData(prev => ({ ...prev, date_from: e.target.value }))}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Date To</label>
                  <input
                    type="date"
                    value={formData.date_to}
                    onChange={(e) => setFormData(prev => ({ ...prev, date_to: e.target.value }))}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {savedSearches.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded">
          <p className="text-gray-500 mb-4">No saved searches found</p>
          <button
            onClick={() => setShowCreateForm(true)}
            className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
          >
            Create Your First Saved Search
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {savedSearches.map(search => (
            <div key={search.id} className="border rounded-lg p-4 bg-white shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold">{search.name}</h3>
                  {search.description && (
                    <p className="text-gray-600 text-sm mt-1">{search.description}</p>
                  )}
                </div>
                <div className="flex items-center space-x-2 ml-4">
                  <span className={`px-2 py-1 rounded text-xs ${search.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                    {search.is_active ? 'Active' : 'Inactive'}
                  </span>
                  <button
                    onClick={() => handleUpdateMatches(search.id)}
                    className="text-blue-500 hover:text-blue-700 text-sm"
                  >
                    Update Matches
                  </button>
                  <button
                    onClick={() => handleDelete(search.id)}
                    className="text-red-500 hover:text-red-700 text-sm"
                  >
                    Delete
                  </button>
                </div>
              </div>

              <div className="flex items-center space-x-4 text-sm text-gray-600 mb-2">
                <span>Query: <strong>"{search.query}"</strong></span>
                {search.item_types && search.item_types.length > 0 && (
                  <div className="flex items-center space-x-1">
                    <span>Types:</span>
                    {search.item_types.map(type => (
                      <span key={type} className={`px-2 py-1 rounded text-xs ${getItemTypeColor(type)}`}>
                        {type}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {(search.date_from || search.date_to) && (
                <div className="text-sm text-gray-600 mb-2">
                  {search.date_from && <span>From: {formatDate(search.date_from)}</span>}
                  {search.date_from && search.date_to && <span> | </span>}
                  {search.date_to && <span>To: {formatDate(search.date_to)}</span>}
                </div>
              )}

              <div className="flex justify-between items-center text-sm text-gray-500">
                <div>
                  <span className="font-semibold text-blue-600">{search.match_count}</span> matches found
                  {search.last_run && (
                    <span> (updated {formatDate(search.last_run)})</span>
                  )}
                </div>
                <div>
                  Created {formatDate(search.created_at)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SavedSearches;