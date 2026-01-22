import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { editionsApi, itemsApi } from '../services/api';
import { Item, ItemType } from '../types';

const EditionDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const editionId = parseInt(id!);
  const [activeTab, setActiveTab] = useState<'stories' | 'ads' | 'classifieds'>('stories');
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
      // Type assertion for axios error structure
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
      // Auto-start processing after reprocess
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

  const handleTabChange = (tab: 'stories' | 'ads' | 'classifieds') => {
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

  const getStatusColor = (status: string) => {
    return `status-${status}`;
  };

  if (editionLoading) {
    return <div className="loading">Loading edition...</div>;
  }

  if (editionError) {
    return <div className="error">Error loading edition: {(editionError as Error).message}</div>;
  }

  if (!edition) {
    return <div className="error">Edition not found</div>;
  }

  return (
    <div>
      <div className="edition-header">
        <h1>{edition.newspaper_name}</h1>
        <div className="edition-meta">
          <span>Date: {formatDate(edition.edition_date)}</span>
          <span>Pages: {edition.num_pages}</span>
          <span className={`status ${getStatusColor(edition.status)}`}>
            {edition.status}
          </span>
        </div>
        <div className="processing-controls">
          {edition.status === 'UPLOADED' && (
            <button
              className="btn"
              onClick={() => processMutation.mutate()}
              disabled={processMutation.isPending}
            >
              {processMutation.isPending ? 'Processing...' : 'Start Processing'}
            </button>
          )}
          {edition.status === 'READY' && (
            <button
              className="btn btn-secondary"
              onClick={() => reprocessMutation.mutate()}
              disabled={reprocessMutation.isPending || processMutation.isPending}
            >
              {reprocessMutation.isPending || processMutation.isPending ? 'Reprocessing...' : 'Reprocess'}
            </button>
          )}
          {edition.status === 'FAILED' && (
            <div>
              <button
                className="btn"
                onClick={() => processMutation.mutate()}
                disabled={processMutation.isPending}
              >
                {processMutation.isPending ? 'Retrying...' : 'Retry Processing'}
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => reprocessMutation.mutate()}
                disabled={reprocessMutation.isPending || processMutation.isPending}
                style={{ marginLeft: '10px' }}
              >
                {reprocessMutation.isPending || processMutation.isPending ? 'Reprocessing...' : 'Reset & Reprocess'}
              </button>
            </div>
          )}
        </div>
        
        {edition.error_message && (
          <div className="error">
            Processing Error: {edition.error_message}
          </div>
        )}

        {edition.status === 'PROCESSING' && (
          <div className="processing-status">
            <div className="status-indicator">
              <span className="pulse"></span>
              Processing in progress...
            </div>
            <p>The edition is being processed. This may take a few minutes.</p>
          </div>
        )}

        {processingStatus && processingStatus.extraction_runs.length > 0 && (
          <div className="extraction-logs">
            <h4>Processing History</h4>
            {processingStatus.extraction_runs.map((run) => (
              <div key={run.id} className={`log-entry ${run.success ? 'success' : 'error'}`}>
                <div className="log-header">
                  <span>Run #{run.id} (v{run.version})</span>
                  <span className={`status ${run.success ? 'success' : 'error'}`}>
                    {run.success ? 'Success' : 'Failed'}
                  </span>
                </div>
                <div className="log-details">
                  Started: {new Date(run.started_at).toLocaleString()}
                  {run.finished_at && (
                    <> • Finished: {new Date(run.finished_at).toLocaleString()}</>
                  )}
                  {!run.finished_at && <> • Still running...</>}
                </div>
                {run.stats && (
                  <div className="log-stats">
                    <strong>Stats:</strong> {JSON.stringify(run.stats, null, 2)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="edition-content">
        <div className="tabs">
          <div
            className={`tab ${activeTab === 'stories' ? 'active' : ''}`}
            onClick={() => handleTabChange('stories')}
          >
            Stories
          </div>
          <div
            className={`tab ${activeTab === 'ads' ? 'active' : ''}`}
            onClick={() => handleTabChange('ads')}
          >
            Advertisements
          </div>
          <div
            className={`tab ${activeTab === 'classifieds' ? 'active' : ''}`}
            onClick={() => handleTabChange('classifieds')}
          >
            Classifieds
          </div>
        </div>

        <div className="items-content">
          {edition.status === 'READY' ? (
            itemsLoading ? (
              <div className="loading">Loading items...</div>
            ) : !items || items.length === 0 ? (
              <p>No {activeTab} found in this edition.</p>
            ) : (
              <div className="items-list">
                {items.map((item: Item) => (
                  <div key={item.id} className="item-card">
                    <h4>
                      {item.title || 'Untitled'}
                      <span className={`item-type type-${item.item_type}`}>
                        {item.item_type}
                        {item.subtype && `: ${item.subtype}`}
                      </span>
                    </h4>
                    <div className="item-meta">
                      Page {item.page_number}
                    </div>
                    {item.text && (
                      <div className="item-text">
                        {item.text.substring(0, 300)}
                        {item.text.length > 300 && '...'}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )
          ) : (
            <div className="processing-message">
              <p>Edition is not ready for viewing.</p>
              <p>Status: {edition.status}</p>
              {edition.status === 'UPLOADED' && (
                <p>Click "Start Processing" to begin text extraction and analysis.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EditionDetail;