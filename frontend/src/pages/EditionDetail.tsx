import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { editionsApi, itemsApi, favoritesApi, collectionsApi } from '../services/api';
import { Item, ItemType, Collection } from '../types';
import { PageContainer } from '../components/layout';
import { Button, Card, StatusBadge, ItemTypeBadge, Loading } from '../components/ui';
import { CategoryList } from '../components/CategoryBadge';

type TabType = 'stories' | 'ads' | 'classifieds';

const EditionDetail = () => {
  const { id } = useParams<{ id: string }>();
  const editionId = parseInt(id!);
  const [activeTab, setActiveTab] = useState<TabType>('stories');
  const [itemFilter, setItemFilter] = useState<{
    item_type?: ItemType;
    subtype?: string;
  }>({ item_type: 'STORY' });

  const [userFavorites, setUserFavorites] = useState<number[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [showCollectionMenu, setShowCollectionMenu] = useState<number | null>(null);

  const queryClient = useQueryClient();

  const { data: edition, isLoading: editionLoading, error: editionError } = useQuery({
    queryKey: ['edition', editionId],
    queryFn: () => editionsApi.getEdition(editionId),
  });

  const { data: processingStatus } = useQuery({
    queryKey: ['processing-status', editionId],
    queryFn: () => editionsApi.getProcessingStatus(editionId),
    enabled: !!edition && (edition.status === 'PROCESSING' || edition.status === 'FAILED'),
    refetchInterval: edition?.status === 'PROCESSING' ? 2000 : false,
  });

  const { data: items, isLoading: itemsLoading } = useQuery({
    queryKey: ['items', editionId, itemFilter],
    queryFn: () => itemsApi.getEditionItems(editionId, itemFilter),
    enabled: !!edition,
  });

  useEffect(() => {
    if (edition) {
      loadUserData();
    }
  }, [edition]);

  const loadUserData = async () => {
    try {
      const [favs, colls] = await Promise.all([
        favoritesApi.getFavorites(0, 100, false),
        collectionsApi.getCollections()
      ]);
      setUserFavorites(favs.map(f => f.item_id));
      setCollections(colls);
    } catch (err) {
      console.error('Failed to load user data', err);
    }
  };

  const toggleFavorite = async (itemId: number) => {
    const isFavorited = userFavorites.includes(itemId);
    try {
      if (isFavorited) {
        await favoritesApi.removeFavoriteByItem(itemId);
        setUserFavorites(userFavorites.filter(id => id !== itemId));
      } else {
        await favoritesApi.addFavorite({ item_id: itemId });
        setUserFavorites([...userFavorites, itemId]);
      }
    } catch (err) {
      console.error('Failed to toggle favorite', err);
    }
  };

  const addItemToCollection = async (collectionId: number, itemId: number) => {
    try {
      await collectionsApi.addItemToCollection(collectionId, { item_id: itemId });
      setShowCollectionMenu(null);
      alert('Added to collection');
    } catch (err) {
      console.error('Failed to add to collection', err);
    }
  };

  const processMutation = useMutation({
    mutationFn: () => editionsApi.processEdition(editionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['edition', editionId] });
      queryClient.invalidateQueries({ queryKey: ['processing-status', editionId] });
      alert('Processing started successfully!');
    },
    onError: (error: unknown) => {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const responseDetail = axiosError.response?.data?.detail;
      alert(`Processing failed: ${responseDetail || errorMessage}`);
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: () => editionsApi.reprocessEdition(editionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['edition', editionId] });
      queryClient.invalidateQueries({ queryKey: ['processing-status', editionId] });
      setTimeout(() => {
        processMutation.mutate();
      }, 500);
    },
    onError: (error: unknown) => {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const responseDetail = axiosError.response?.data?.detail;
      alert(`Reprocess failed: ${responseDetail || errorMessage}`);
    },
  });

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    const filter: { item_type?: ItemType; subtype?: string } = {};

    switch (tab) {
      case 'stories':
        filter.item_type = 'STORY';
        break;
      case 'ads':
        filter.item_type = 'AD';
        break;
      case 'classifieds':
        filter.item_type = 'CLASSIFIED';
        break;
    }

    setItemFilter(filter);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getNumber = (value: unknown) =>
    typeof value === 'number' && Number.isFinite(value) ? value : undefined;

  const latestRunStats = processingStatus?.extraction_runs?.[0]?.stats as
    | Record<string, unknown>
    | undefined;
  const totalPages = getNumber(latestRunStats?.total_pages);
  const pagesProcessed = getNumber(latestRunStats?.pages_processed);
  const progressPct =
    totalPages && pagesProcessed !== undefined
      ? Math.min(100, Math.round((pagesProcessed / totalPages) * 100))
      : undefined;

  if (editionLoading) {
    return (
      <PageContainer>
        <Loading message="Loading edition..." />
      </PageContainer>
    );
  }

  if (editionError) {
    return (
      <PageContainer>
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          Error loading edition: {(editionError as Error).message}
        </div>
      </PageContainer>
    );
  }

  if (!edition) {
    return (
      <PageContainer>
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          Edition not found
        </div>
      </PageContainer>
    );
  }

  const tabs: { key: TabType; label: string }[] = [
    { key: 'stories', label: 'Stories' },
    { key: 'ads', label: 'Advertisements' },
    { key: 'classifieds', label: 'Classifieds' },
  ];

  return (
    <PageContainer>
      {/* Breadcrumb */}
      <div className="mb-4">
        <Link to="/" className="text-ink-700 hover:text-ink-800 text-sm">
          &larr; Back to Editions
        </Link>
      </div>

      {/* Edition Header */}
      <Card className="mb-6">
        <div className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-4">
            <div>
              <h1 className="text-2xl font-bold text-ink-800 mb-2">{edition.newspaper_name}</h1>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-stone-600">
                <span>Edition: {formatDate(edition.edition_date)}</span>
                <span>{edition.num_pages} pages</span>
                <StatusBadge status={edition.status as any} />
              </div>
            </div>

            {/* Processing Controls */}
            <div className="flex flex-wrap gap-2">
              {edition.status === 'UPLOADED' && (
                <Button
                  onClick={() => processMutation.mutate()}
                  isLoading={processMutation.isPending}
                >
                  Start Processing
                </Button>
              )}
              {edition.status === 'READY' && (
                <Button
                  variant="secondary"
                  onClick={() => reprocessMutation.mutate()}
                  isLoading={reprocessMutation.isPending || processMutation.isPending}
                >
                  Reprocess
                </Button>
              )}
              {edition.status === 'FAILED' && (
                <>
                  <Button
                    onClick={() => processMutation.mutate()}
                    isLoading={processMutation.isPending}
                  >
                    Retry Processing
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => reprocessMutation.mutate()}
                    isLoading={reprocessMutation.isPending || processMutation.isPending}
                  >
                    Reset & Reprocess
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* Error Message */}
          {edition.error_message && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
              <strong>Processing Error:</strong> {edition.error_message}
            </div>
          )}

          {/* Processing Status */}
          {edition.status === 'PROCESSING' && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg mt-4">
              <div className="flex items-center gap-2 font-medium text-amber-800 mb-1">
                <span className="pulse-dot"></span>
                Processing in progress...
              </div>
              <p className="text-amber-700 text-sm">
                The edition is being processed. This may take a few minutes.
              </p>
              {totalPages && pagesProcessed !== undefined && progressPct !== undefined && (
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs text-amber-700 mb-1">
                    <span>Progress</span>
                    <span>
                      {progressPct}% ({pagesProcessed}/{totalPages} pages)
                    </span>
                  </div>
                  <div className="h-2 w-full bg-amber-100 rounded">
                    <div
                      className="h-2 bg-amber-400 rounded"
                      style={{ width: `${progressPct}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </Card>

      {/* Content Tabs */}
      <Card>
        {/* Tab Navigation */}
        <div className="flex border-b border-stone-200">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => handleTabChange(tab.key)}
              className={`
                px-6 py-3 text-sm font-medium transition-colors
                ${activeTab === tab.key
                  ? 'text-ink-800 border-b-2 border-ink-800 -mb-px'
                  : 'text-stone-500 hover:text-ink-700 hover:bg-stone-50'
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="p-4">
          {edition.status === 'READY' ? (
            itemsLoading ? (
              <Loading message="Loading items..." />
            ) : !items || items.length === 0 ? (
              <div className="text-center py-8 text-stone-500">
                No {activeTab} found in this edition.
              </div>
            ) : (
              <div className="space-y-4">
                {items.map((item: any) => (
                  <div
                    key={item.id}
                    className="p-4 border border-stone-200 rounded-lg hover:border-stone-300 transition-colors"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 mb-2">
                      <h4 className="font-semibold text-ink-800">
                        {item.title || 'Untitled'}
                      </h4>
                      <div className="flex items-center gap-2">
                        <ItemTypeBadge type={item.item_type} />
                        {item.subtype && (
                          <span className="text-xs text-stone-500">{item.subtype}</span>
                        )}
                      </div>
                    </div>
                    <div className="text-sm text-stone-500 mb-2">Page {item.page_number}</div>

                    {item.categories && item.categories.length > 0 && (
                      <div className="mb-2">
                        <CategoryList
                          categories={item.categories}
                          showConfidence={true}
                          maxDisplay={5}
                          size="sm"
                        />
                      </div>
                    )}

                    {item.text && (
                      <p className="text-sm text-stone-600 leading-relaxed">
                        {item.text.substring(0, 300)}
                        {item.text.length > 300 && '...'}
                      </p>
                    )}

                    <div className="mt-4 flex items-center justify-end space-x-3">
                      <button
                        onClick={() => toggleFavorite(item.id)}
                        className={`p-1.5 rounded-full transition-colors ${userFavorites.includes(item.id)
                            ? 'text-red-500 hover:bg-red-50'
                            : 'text-gray-400 hover:bg-gray-100'
                          }`}
                        title={userFavorites.includes(item.id) ? "Remove from Favorites" : "Add to Favorites"}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill={userFavorites.includes(item.id) ? "currentColor" : "none"} stroke="currentColor">
                          <path fillRule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clipRule="evenodd" />
                        </svg>
                      </button>

                      <div className="relative">
                        <button
                          onClick={() => setShowCollectionMenu(showCollectionMenu === item.id ? null : item.id)}
                          className="p-1.5 text-gray-400 hover:bg-gray-100 rounded-full transition-colors"
                          title="Add to Collection"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </button>

                        {showCollectionMenu === item.id && (
                          <div className="absolute right-0 bottom-full mb-2 w-48 bg-white border border-gray-200 rounded-lg shadow-xl z-10 py-1 overflow-hidden">
                            <div className="px-3 py-1.5 text-xs font-bold text-gray-500 uppercase bg-gray-50 border-b border-gray-100">Add to Collection</div>
                            {collections.length === 0 ? (
                              <Link to="/app/collections" className="block px-3 py-2 text-sm text-blue-600 hover:bg-blue-50">Create first collection</Link>
                            ) : (
                              collections.map(col => (
                                <button
                                  key={col.id}
                                  onClick={() => addItemToCollection(col.id, item.id)}
                                  className="block w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-blue-50 transition-colors truncate"
                                  style={{ borderLeft: `3px solid ${col.color}` }}
                                >
                                  {col.name}
                                </button>
                              ))
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            <div className="text-center py-12">
              <p className="text-stone-600 mb-2">Edition is not ready for viewing.</p>
              <p className="text-stone-500 text-sm mb-4">Status: {edition.status}</p>
              {edition.status === 'UPLOADED' && (
                <p className="text-stone-500 text-sm">
                  Click "Start Processing" above to begin text extraction and analysis.
                </p>
              )}
            </div>
          )}
        </div>
      </Card>
    </PageContainer>
  );
};

export default EditionDetail;
