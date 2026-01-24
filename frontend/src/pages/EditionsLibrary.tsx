import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { editionsApi } from '../services/api';
import { Edition } from '../types';
import { PageContainer, PageHeader } from '../components/layout';
import { Button, Input, Card, StatusBadge, Loading } from '../components/ui';

const EditionsLibrary = () => {
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
      setFile(null);
      setNewspaperName('');
      setEditionDate('');
      alert('Edition uploaded successfully! Processing will begin shortly.');
    },
    onError: (error: unknown) => {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const responseDetail = axiosError.response?.data?.detail;
      alert(`Upload failed: ${responseDetail || errorMessage}`);
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

  if (isLoading) {
    return (
      <PageContainer>
        <Loading message="Loading editions..." />
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer>
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          Error loading editions: {(error as Error).message}
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      {/* Upload Section */}
      <Card className="mb-8">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-ink-800 mb-4">Upload Newspaper Edition</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-ink-800 mb-1.5">
                  PDF File
                </label>
                <div className="border-2 border-dashed border-stone-300 rounded-lg p-4 text-center hover:border-stone-400 transition-colors">
                  <input
                    type="file"
                    id="edition-file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <label htmlFor="edition-file" className="cursor-pointer text-sm">
                    {file ? (
                      <span className="text-ink-800 font-medium">{file.name}</span>
                    ) : (
                      <span className="text-stone-500">Click to select PDF</span>
                    )}
                  </label>
                </div>
              </div>

              <Input
                label="Newspaper Name"
                type="text"
                value={newspaperName}
                onChange={(e) => setNewspaperName(e.target.value)}
                placeholder="e.g., The Daily Gazette"
                required
              />

              <Input
                label="Edition Date"
                type="date"
                value={editionDate}
                onChange={(e) => setEditionDate(e.target.value)}
                required
              />
            </div>

            <Button type="submit" isLoading={uploadMutation.isPending}>
              {uploadMutation.isPending ? 'Uploading...' : 'Upload Edition'}
            </Button>
          </form>
        </div>
      </Card>

      {/* Summary Statistics */}
      {editions && editions.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-8">
          <Card className="p-4 text-center">
            <div className="text-3xl font-bold text-ink-800">{editions.length}</div>
            <div className="text-sm text-stone-600">Total Editions</div>
          </Card>
          <Card className="p-4 text-center">
            <div className="text-3xl font-bold text-ink-800">
              {editions.reduce((sum, e) => sum + e.num_pages, 0)}
            </div>
            <div className="text-sm text-stone-600">Total Pages</div>
          </Card>
          <Card className="p-4 text-center">
            <div className="text-3xl font-bold text-ink-800">
              {editions.filter(e => e.status === 'READY').length}
            </div>
            <div className="text-sm text-stone-600">Processed</div>
          </Card>
        </div>
      )}

      {/* Editions Grid */}
      <div>
        <PageHeader title="Editions Library" />

        {!editions || editions.length === 0 ? (
          <Card>
            <div className="p-8 text-center text-stone-500">
              No editions uploaded yet. Upload your first newspaper edition above.
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {editions.map((edition: Edition) => (
              <Link key={edition.id} to={`/edition/${edition.id}`}>
                <Card hover className="h-full">
                  <div className="flex justify-between items-start mb-3">
                    <h3 className="text-lg font-semibold text-ink-800 line-clamp-1">
                      {edition.newspaper_name}
                    </h3>
                    <StatusBadge status={edition.status as 'UPLOADED' | 'PROCESSING' | 'READY' | 'FAILED'} />
                  </div>

                  <div className="space-y-1 text-sm text-stone-600">
                    <div className="flex justify-between">
                      <span>Edition Date:</span>
                      <span className="font-medium">{formatDate(edition.edition_date)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Pages:</span>
                      <span className="font-medium">{edition.num_pages}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Uploaded:</span>
                      <span className="font-medium">{formatDate(edition.created_at)}</span>
                    </div>
                  </div>

                  {edition.error_message && (
                    <div className="mt-3 p-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded">
                      {edition.error_message}
                    </div>
                  )}
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </PageContainer>
  );
};

export default EditionsLibrary;
