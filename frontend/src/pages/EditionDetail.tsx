import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { editionsApi, itemsApi, favoritesApi, collectionsApi } from '../services/api';
import { ItemType, Collection, EditionStatus, Item, StoryGroup, PageMetrics, Page } from '../types';
import { PageContainer } from '../components/layout';
import { Button, Card, StatusBadge, ItemTypeBadge, Loading } from '../components/ui';
import { CategoryList } from '../components/CategoryBadge';
import { useAuth } from '../context/AuthContext';

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
  const [expandedStories, setExpandedStories] = useState<number[]>([]);
  const [selectedPage, setSelectedPage] = useState<number | null>(null);
  const [pagePreview, setPagePreview] = useState<Page | null>(null);

  const queryClient = useQueryClient();
  const { isAdmin } = useAuth();
  const isAdminUser = isAdmin();

  const { data: edition, isLoading: editionLoading, error: editionError } = useQuery({
    queryKey: ['edition', editionId],
    queryFn: () => editionsApi.getEdition(editionId),
    refetchInterval: (query) =>
      query.state.data?.status === 'PROCESSING' || query.state.data?.status === 'UPLOADED'
        ? 2000
        : false,
  });

  const { data: items, isLoading: itemsLoading } = useQuery({
    queryKey: ['items', editionId, itemFilter],
    queryFn: () => itemsApi.getEditionItems(editionId, itemFilter),
    enabled: !!edition && activeTab !== 'stories',
  });

  const { data: storyGroups, isLoading: storyGroupsLoading } = useQuery({
    queryKey: ['story-groups', editionId],
    queryFn: () => itemsApi.getStoryGroups(editionId),
    enabled: !!edition && activeTab === 'stories',
  });

  const { data: pageMetrics } = useQuery({
    queryKey: ['edition-pages', editionId],
    queryFn: () => editionsApi.getEditionPageMetrics(editionId),
    enabled: !!edition,
    refetchInterval: (query) =>
      query.state.data && (edition?.status === 'PROCESSING' || edition?.status === 'UPLOADED')
        ? 5000
        : false,
  });

  const { data: pageDetail } = useQuery({
    queryKey: ['edition-page', editionId, selectedPage],
    queryFn: () => editionsApi.getEditionPage(editionId, selectedPage as number),
    enabled: !!edition && selectedPage !== null,
  });

  useEffect(() => {
    if (pageDetail) setPagePreview(pageDetail);
  }, [pageDetail]);

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

  const toggleStoryExpansion = (groupId: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (expandedStories.includes(groupId)) {
      setExpandedStories(expandedStories.filter(id => id !== groupId));
    } else {
      setExpandedStories([...expandedStories, groupId]);
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
      // Processing is now started automatically by the backend
    },
    onError: (error: unknown) => {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const responseDetail = axiosError.response?.data?.detail;
      alert(`Reprocess failed: ${responseDetail || errorMessage}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => editionsApi.deleteEdition(editionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['editions'] });
      alert('Edition deleted successfully');
      window.location.href = '/app/editions';
    },
    onError: (error: unknown) => {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const responseDetail = axiosError.response?.data?.detail;
      alert(`Delete failed: ${responseDetail || errorMessage}`);
    },
  });

  const archiveMutation = useMutation({
    mutationFn: () => editionsApi.archiveEdition(editionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['edition', editionId] });
      alert('Archive started.');
    },
    onError: (error: unknown) => {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const responseDetail = axiosError.response?.data?.detail;
      alert(`Archive failed: ${responseDetail || errorMessage}`);
    },
  });

  const handleDelete = () => {
    if (window.confirm(`Are you sure you want to delete "${edition?.newspaper_name}"? This action cannot be undone.`)) {
      deleteMutation.mutate();
    }
  };

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

  const getConfidenceColor = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '#e7e5e4';
    if (value >= 85) return '#16a34a';
    if (value >= 70) return '#f59e0b';
    return '#ef4444';
  };

  const confidenceSummary = (metrics?: PageMetrics[]) => {
    if (!metrics || metrics.length === 0) return { avg: null, lowCount: 0 };
    const confs = metrics.map(m => m.ocr_confidence).filter((v): v is number => typeof v === 'number');
    const avg = confs.length ? Math.round((confs.reduce((a, b) => a + b, 0) / confs.length) * 100) / 100 : null;
    const lowCount = confs.filter(v => v < 70).length;
    return { avg, lowCount };
  };

  const getImageUrl = (imagePath?: string | null) => {
    if (!imagePath) return null;
    if (imagePath.startsWith('/files/')) return imagePath;
    const idx = imagePath.indexOf('storage/');
    if (idx >= 0) return `/files/${imagePath.slice(idx + 'storage/'.length)}`;
    if (imagePath.startsWith('./storage/')) return `/files/${imagePath.slice('./storage/'.length)}`;
    return imagePath;
  };

  const lowConfidencePages = (pageMetrics || []).filter(
    page => typeof page.ocr_confidence === 'number' && (page.ocr_confidence as number) < 70
  );

  const reprocessPageMutation = useMutation({
    mutationFn: (pageNumber: number) => editionsApi.reprocessEditionPage(editionId, pageNumber),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['edition-pages', editionId] });
      if (selectedPage) {
        queryClient.invalidateQueries({ queryKey: ['edition-page', editionId, selectedPage] });
      }
    },
    onError: (error: unknown) => {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const responseDetail = axiosError.response?.data?.detail;
      alert(`Re-OCR failed: ${responseDetail || errorMessage}`);
    },
  });

  const totalPages = edition?.total_pages ?? 0;
  const pagesProcessed = edition?.processed_pages ?? 0;
  const stageLabel = edition?.current_stage ?? 'QUEUED';
  const progressPct =
    totalPages > 0
      ? Math.min(100, Math.round((pagesProcessed / totalPages) * 100))
      : 0;
  const showProgress = edition?.status === 'UPLOADED' || edition?.status === 'PROCESSING';

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
                <span>{edition.total_pages} pages</span>
                <StatusBadge status={edition.status as EditionStatus} />
                {edition.archive_status && (
                  <span className="text-xs text-stone-500">Archive: {edition.archive_status}</span>
                )}
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
              {isAdminUser && edition.status === 'READY' && (edition.archive_status === 'SCHEDULED' || edition.archive_status === 'ARCHIVE_FAILED') && (
                <Button
                  variant="secondary"
                  onClick={() => archiveMutation.mutate()}
                  isLoading={archiveMutation.isPending}
                >
                  Archive Now
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
              {/* Delete button - always visible except during processing */}
              {edition.status !== 'PROCESSING' && (
                <Button
                  variant="secondary"
                  onClick={handleDelete}
                  isLoading={deleteMutation.isPending}
                  className="text-red-600 hover:bg-red-50"
                >
                  Delete
                </Button>
              )}
            </div>
          </div>

          {/* Error Message */}
          {edition.last_error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
              <strong>Processing Error:</strong> {edition.last_error}
            </div>
          )}

          {/* Processing Status */}
          {showProgress && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg mt-4">
              <div className="flex items-center gap-2 font-medium text-amber-800 mb-1">
                <span className="pulse-dot"></span>
                {edition.status === 'UPLOADED' ? 'Queued for processing...' : 'Processing in progress...'}
              </div>
              <p className="text-amber-700 text-sm">
                The edition is being processed. This may take a few minutes.
              </p>
              {totalPages && pagesProcessed !== undefined && progressPct !== undefined && (
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs text-amber-700 mb-1">
                    <span>Processed {pagesProcessed} of {totalPages} pages</span>
                    <span>{stageLabel}</span>
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

      <Card className="mb-6">
        <div className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
            <div>
              <h2 className="text-lg font-semibold text-ink-800">OCR Confidence Heatmap</h2>
              <p className="text-sm text-stone-500">
                Each square represents a page. Color reflects average OCR confidence.
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs text-stone-600">
              <div className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: '#16a34a' }} />
                High
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: '#f59e0b' }} />
                Medium
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: '#ef4444' }} />
                Low
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: '#e7e5e4' }} />
                Unknown
              </div>
            </div>
          </div>

          {pageMetrics && pageMetrics.length > 0 ? (
            <>
              <div className="flex flex-wrap gap-1">
                {pageMetrics.map((page) => {
                  const conf = page.ocr_confidence;
                  const tooltip = [
                    `Page ${page.page_number}`,
                    page.ocr_used ? `OCR: ${conf ?? 'n/a'}` : 'OCR: not used',
                    page.ocr_engine ? `Engine: ${page.ocr_engine}` : null,
                    page.char_count ? `Chars: ${page.char_count}` : null,
                  ].filter(Boolean).join(' | ');
                  return (
                    <span
                      key={page.page_number}
                      title={tooltip}
                      className="h-3.5 w-3.5 rounded-sm border border-white cursor-pointer"
                      style={{ backgroundColor: getConfidenceColor(conf ?? null) }}
                      onClick={() => setSelectedPage(page.page_number)}
                    />
                  );
                })}
              </div>
              {(() => {
                const summary = confidenceSummary(pageMetrics);
                return (
                  <div className="mt-3 text-xs text-stone-500">
                    {summary.avg !== null ? `Average confidence: ${summary.avg}` : 'Average confidence: n/a'}
                    {summary.lowCount > 0 && ` • Low-confidence pages: ${summary.lowCount}`}
                  </div>
                );
              })()}

              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-sm font-medium text-stone-700">Low-confidence pages</div>
                  {isAdminUser && lowConfidencePages.length > 0 && (
                    <button
                      className="text-xs text-blue-600 hover:text-blue-700"
                      onClick={() => lowConfidencePages.forEach(p => reprocessPageMutation.mutate(p.page_number))}
                    >
                      Re-OCR all
                    </button>
                  )}
                </div>
                {lowConfidencePages.length === 0 ? (
                  <div className="text-xs text-stone-500">No low-confidence pages detected.</div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {lowConfidencePages.map(page => (
                      <div
                        key={`low-${page.page_number}`}
                        className="flex items-center gap-2 px-2 py-1 rounded border border-stone-200 text-xs text-stone-700"
                      >
                        <button
                          className="text-blue-600 hover:text-blue-700"
                          onClick={() => setSelectedPage(page.page_number)}
                        >
                          Page {page.page_number}
                        </button>
                        {isAdminUser && (
                          <button
                            className="text-xs text-stone-500 hover:text-stone-700"
                            onClick={() => reprocessPageMutation.mutate(page.page_number)}
                          >
                            Re-OCR
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="text-sm text-stone-500">No page metrics yet. Process an edition to populate this view.</div>
          )}
        </div>
      </Card>

      {selectedPage !== null && pagePreview && (
        <div
          className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center"
          onClick={() => setSelectedPage(null)}
        >
          <div
            className="bg-white rounded-xl shadow-xl w-[92vw] max-w-6xl max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-3 border-b border-stone-200">
              <div className="text-sm font-semibold text-ink-800">
                Page {pagePreview.page_number} Preview
              </div>
              <div className="flex items-center gap-3">
                {isAdminUser && (
                  <button
                    className="text-xs text-stone-600 hover:text-stone-800"
                    onClick={() => reprocessPageMutation.mutate(pagePreview.page_number)}
                  >
                    Re-OCR
                  </button>
                )}
                <button
                  className="text-sm text-stone-500 hover:text-stone-700"
                  onClick={() => setSelectedPage(null)}
                >
                  Close
                </button>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-0">
              <div className="border-r border-stone-200 p-4 overflow-auto max-h-[75vh] bg-stone-50">
                {getImageUrl(pagePreview.image_path) ? (
                  <img
                    src={getImageUrl(pagePreview.image_path) as string}
                    alt={`Page ${pagePreview.page_number}`}
                    className="w-full h-auto shadow-md"
                  />
                ) : (
                  <div className="text-sm text-stone-500">No page image available.</div>
                )}
              </div>
              <div className="p-4 overflow-auto max-h-[75vh]">
                <div className="text-xs text-stone-500 mb-2">
                  OCR Text
                </div>
                <pre className="text-sm text-stone-700 whitespace-pre-wrap font-sans">
                  {pagePreview.extracted_text || 'No extracted text available.'}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

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
          {edition.status === 'READY' || edition.status === 'PROCESSING' || edition.status === 'ARCHIVED' ? (
            activeTab === 'stories' ? (
              storyGroupsLoading ? (
                <Loading message="Loading stories..." />
              ) : !storyGroups || storyGroups.length === 0 ? (
                <div className="text-center py-8 text-stone-500">
                  No stories found in this edition.
                </div>
              ) : (
                <div className="space-y-4">
                  {storyGroups.map((group: StoryGroup) => {
                    const isExpanded = expandedStories.includes(group.group_id);
                    return (
                      <div
                        key={group.group_id}
                        className="block p-4 border border-stone-200 rounded-lg hover:border-stone-300 transition-colors"
                      >
                        <div
                          className="flex items-start justify-between gap-3 mb-2 cursor-pointer"
                          onClick={(e) => toggleStoryExpansion(group.group_id, e)}
                        >
                          <div className="flex-1">
                            <h4 className="font-semibold text-ink-800 flex items-center gap-2">
                              {group.title || 'Untitled Story'}
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            </h4>
                            <span className="text-xs text-stone-500">
                              {group.pages.length > 0 ? `Pages ${group.pages.join(', ')}` : 'Pages unknown'}
                            </span>
                          </div>
                          <Link
                            to={`/app/stories/${editionId}/${group.group_id}`}
                            className="text-xs text-ink-700 hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            Open focused view
                          </Link>
                        </div>
                        <div className="mt-2">
                          <p className={`text-sm text-stone-600 leading-relaxed ${isExpanded ? '' : 'line-clamp-3'}`}>
                            {isExpanded ? (group.full_text || group.excerpt) : group.excerpt}
                          </p>
                          {isExpanded && group.full_text && (
                            <div className="mt-4 pt-4 border-t border-stone-100 flex justify-end">
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={(e) => toggleStoryExpansion(group.group_id, e)}
                              >
                                Collapse
                              </Button>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )
            ) : (
              itemsLoading ? (
                <Loading message="Loading items..." />
              ) : !items || items.length === 0 ? (
                <div className="text-center py-8 text-stone-500">
                  No {activeTab} found in this edition.
                </div>
              ) : (
                <div className="space-y-4">
                  {items.map((item: Item) => (
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
