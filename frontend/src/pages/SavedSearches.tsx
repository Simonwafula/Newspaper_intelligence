import { useState, useEffect } from 'react';
import { savedSearchesApi } from '../services/api';
import { SavedSearch, SavedSearchCreate, ItemType } from '../types';
import { PageContainer, PageHeader } from '../components/layout';
import { Button, Input, Textarea, Card, Badge, Loading } from '../components/ui';

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
    } catch {
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
    } catch {
      setError('Failed to create saved search');
    }
  };

  const handleDelete = async (id: number) => {
    if (confirm('Are you sure you want to delete this saved search?')) {
      try {
        await savedSearchesApi.deleteSavedSearch(id);
        loadSavedSearches();
      } catch {
        setError('Failed to delete saved search');
      }
    }
  };

  const handleUpdateMatches = async (id: number) => {
    try {
      await savedSearchesApi.updateSearchMatches(id);
      loadSavedSearches();
    } catch {
      setError('Failed to update matches');
    }
  };

  const handleUpdateAllMatches = async () => {
    try {
      await savedSearchesApi.updateAllSearchMatches();
      loadSavedSearches();
    } catch {
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

  const getItemTypeVariant = (itemType: ItemType): 'blue' | 'amber' | 'purple' | 'default' => {
    switch (itemType) {
      case 'STORY': return 'blue';
      case 'AD': return 'amber';
      case 'CLASSIFIED': return 'purple';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <PageContainer maxWidth="4xl">
        <Loading message="Loading saved searches..." />
      </PageContainer>
    );
  }

  return (
    <PageContainer maxWidth="4xl">
      <PageHeader
        title="Saved Searches"
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={handleUpdateAllMatches}>
              Update All Matches
            </Button>
            <Button onClick={() => setShowCreateForm(true)}>
              Create Saved Search
            </Button>
          </div>
        }
      />

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Create Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-ink-800 mb-6">Create Saved Search</h2>
              <form onSubmit={handleCreate} className="space-y-4">
                <Input
                  label="Name"
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Enter a name for this search"
                />

                <Textarea
                  label="Description"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Optional description"
                />

                <Input
                  label="Search Query"
                  type="text"
                  required
                  value={formData.query}
                  onChange={(e) => setFormData(prev => ({ ...prev, query: e.target.value }))}
                  placeholder="Enter search terms..."
                />

                <div>
                  <label className="block text-sm font-medium text-ink-800 mb-2">Item Types</label>
                  <div className="flex flex-wrap gap-3">
                    {(['STORY', 'AD', 'CLASSIFIED'] as const).map(type => (
                      <label key={type} className="inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.item_types?.includes(type) || false}
                          onChange={() => handleItemTypeChange(type)}
                          className="w-4 h-4 rounded text-ink-800 focus:ring-ink-800 mr-2"
                        />
                        <Badge variant={getItemTypeVariant(type)}>{type}</Badge>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Date From"
                    type="date"
                    value={formData.date_from}
                    onChange={(e) => setFormData(prev => ({ ...prev, date_from: e.target.value }))}
                  />
                  <Input
                    label="Date To"
                    type="date"
                    value={formData.date_to}
                    onChange={(e) => setFormData(prev => ({ ...prev, date_to: e.target.value }))}
                  />
                </div>

                <div className="flex justify-end gap-2 pt-4">
                  <Button type="button" variant="secondary" onClick={() => setShowCreateForm(false)}>
                    Cancel
                  </Button>
                  <Button type="submit">
                    Create
                  </Button>
                </div>
              </form>
            </div>
          </Card>
        </div>
      )}

      {/* Saved Searches List */}
      {savedSearches.length === 0 ? (
        <Card>
          <div className="p-12 text-center">
            <p className="text-stone-500 mb-4">No saved searches found</p>
            <Button onClick={() => setShowCreateForm(true)}>
              Create Your First Saved Search
            </Button>
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          {savedSearches.map(search => (
            <Card key={search.id}>
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-3">
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-ink-800">{search.name}</h3>
                  {search.description && (
                    <p className="text-stone-600 text-sm mt-1">{search.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <Badge variant={search.is_active ? 'green' : 'default'}>
                    {search.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                  <Button variant="ghost" size="sm" onClick={() => handleUpdateMatches(search.id)}>
                    Update
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(search.id)}>
                    Delete
                  </Button>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-stone-600 mb-3">
                <span>Query: <strong className="text-ink-800">"{search.query}"</strong></span>
                {search.item_types && search.item_types.length > 0 && (
                  <div className="flex items-center gap-1">
                    <span>Types:</span>
                    {search.item_types.map(type => (
                      <Badge key={type} variant={getItemTypeVariant(type)}>{type}</Badge>
                    ))}
                  </div>
                )}
              </div>

              {(search.date_from || search.date_to) && (
                <div className="text-sm text-stone-600 mb-3">
                  {search.date_from && <span>From: {formatDate(search.date_from)}</span>}
                  {search.date_from && search.date_to && <span className="mx-2">|</span>}
                  {search.date_to && <span>To: {formatDate(search.date_to)}</span>}
                </div>
              )}

              <div className="flex flex-wrap justify-between items-center text-sm text-stone-500 pt-3 border-t border-stone-100">
                <div>
                  <span className="font-semibold text-ink-800">{search.match_count}</span> matches
                  {search.last_run && (
                    <span className="ml-1">(updated {formatDate(search.last_run)})</span>
                  )}
                </div>
                <div>Created {formatDate(search.created_at)}</div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </PageContainer>
  );
};

export default SavedSearches;
