import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { editionsApi } from '../services/api';
import { Edition } from '../types';

const EditionsLibrary: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [newspaperName, setNewspaperName] = useState('');
  const [editionDate, setEditionDate] = useState('');

  const queryClient = useQueryClient();

  const { data: editions, isLoading, error } = useQuery({
    queryKey: ['editions'],
    queryFn: () => editionsApi.getEditions(),
  });

  const uploadMutation = useMutation({
    mutationFn: (data: { file: File; newspaperName: string; editionDate: string }) =>
      editionsApi.uploadEdition(data.file, data.newspaperName, data.editionDate),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['editions'] });
      // Reset form
      setFile(null);
      setNewspaperName('');
      setEditionDate('');
      alert('Edition uploaded successfully! Processing will begin shortly.');
    },
    onError: (error: any) => {
      alert(`Upload failed: ${error.response?.data?.detail || error.message}`);
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
    } else {
      alert('Please select a PDF file');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !newspaperName || !editionDate) {
      alert('Please fill in all fields');
      return;
    }

    uploadMutation.mutate({ file, newspaperName, editionDate });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getStatusColor = (status: string) => {
    return `status-${status}`;
  };

  if (isLoading) {
    return <div className="loading">Loading editions...</div>;
  }

  if (error) {
    return <div className="error">Error loading editions: {(error as Error).message}</div>;
  }

  return (
    <div>
      <div className="upload-form">
        <h2>Upload Newspaper Edition</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="file">PDF File:</label>
            <input
              type="file"
              id="file"
              accept=".pdf"
              onChange={handleFileChange}
            />
          </div>
          <div className="form-group">
            <label htmlFor="newspaperName">Newspaper Name:</label>
            <input
              type="text"
              id="newspaperName"
              value={newspaperName}
              onChange={(e) => setNewspaperName(e.target.value)}
              placeholder="e.g., The Daily Gazette"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="editionDate">Edition Date:</label>
            <input
              type="date"
              id="editionDate"
              value={editionDate}
              onChange={(e) => setEditionDate(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn" disabled={uploadMutation.isPending}>
            {uploadMutation.isPending ? 'Uploading...' : 'Upload Edition'}
          </button>
        </form>
      </div>

      <div className="editions-section">
        <h2>Editions Library</h2>
        {!editions || editions.length === 0 ? (
          <p>No editions uploaded yet.</p>
        ) : (
          <div className="editions-grid">
            {editions.map((edition: Edition) => (
              <Link key={edition.id} to={`/edition/${edition.id}`} className="edition-card">
                <h3>{edition.newspaper_name}</h3>
                <div className="meta">
                  <div>Date: {formatDate(edition.edition_date)}</div>
                  <div>Pages: {edition.num_pages}</div>
                  <div>Created: {formatDate(edition.created_at)}</div>
                </div>
                <div className={`status ${getStatusColor(edition.status)}`}>
                  {edition.status}
                </div>
                {edition.error_message && (
                  <div className="error-message">
                    Error: {edition.error_message}
                  </div>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default EditionsLibrary;