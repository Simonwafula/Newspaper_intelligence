import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { editionsApi, itemsApi } from '../services/api';
import { Item, ItemType } from '../types';
import { PageContainer } from '../components/layout';
import { Button, Card, StatusBadge, ItemTypeBadge, Loading } from '../components/ui';

type TabType = 'stories' | 'ads' | 'classifieds';

const EditionDetail = () => {
  const { id } = useParams<{ id: string }>();
  const editionId = parseInt(id!);
  const [activeTab, setActiveTab] = useState<TabType>('stories');
  const [itemFilter, setItemFilter] = useState<{
    item_type?: ItemType;
    subtype?: string;
  }>({ item_type: 'STORY' });

  const queryClient = useQueryClient();

  const { data: edition, isLoading: editionLoading, error: editionError } = useQuery({
    queryKey: ['edition', editionId],
    queryFn: () => editionsApi.getEdition(editionId),
  });

  const { data: processingStatus } = useQuery({
    queryKey: ['processing-status', editionId],
    queryFn: () => editionsApi.getProcessingStatus(editionId),
    enabled: !!edition && (edition.status === 'PROCESSING' || edition.status === 'FAILED'),
  });

  const { data: items, isLoading: itemsLoading } = useQuery({
    queryKey: ['items', editionId, itemFilter],
    queryFn: () => itemsApi.getEditionItems(editionId, itemFilter),
    enabled: !!edition,
  });

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
                <StatusBadge status={edition.status as 'UPLOADED' | 'PROCESSING' | 'READY' | 'FAILED'} />
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
            </div>
          )}

          {/* Processing History */}
          {processingStatus && processingStatus.extraction_runs.length > 0 && (
            <div className="mt-6">
              <h4 className="text-sm font-semibold text-ink-800 mb-3">Processing History</h4>
              <div className="space-y-3">
                {processingStatus.extraction_runs.map((run) => (
                  <div
                    key={run.id}
                    className={`p-3 rounded-lg border ${
                      run.success
                        ? 'bg-green-50 border-green-200'
                        : 'bg-red-50 border-red-200'
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-sm font-medium">
                        Run #{run.id} (v{run.version})
                      </span>
                      <span
                        className={`text-xs font-medium ${
                          run.success ? 'text-green-700' : 'text-red-700'
                        }`}
                      >
                        {run.success ? 'Success' : 'Failed'}
                      </span>
                    </div>
                    <div className="text-xs text-stone-600">
                      Started: {new Date(run.started_at).toLocaleString()}
                      {run.finished_at && (
                        <> &bull; Finished: {new Date(run.finished_at).toLocaleString()}</>
                      )}
                      {!run.finished_at && <> &bull; Still running...</>}
                    </div>
                    {run.stats && (
                      <pre className="mt-2 p-2 bg-white/50 rounded text-xs font-mono overflow-x-auto">
                        {JSON.stringify(run.stats, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
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
                    {item.text && (
                      <p className="text-sm text-stone-600 leading-relaxed">
                        {item.text.substring(0, 300)}
                        {item.text.length > 300 && '...'}
                      </p>
                    )}
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
