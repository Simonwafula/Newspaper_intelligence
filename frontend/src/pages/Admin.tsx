import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { editionsApi } from '../services/api';
import { PageContainer, PageHeader } from '../components/layout';
import { Button, Input, Card, CardHeader, CardTitle, CardContent, StatusBadge } from '../components/ui';

const Admin = () => {
  const [token, setToken] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [newspaperName, setNewspaperName] = useState('');
  const [editionDate, setEditionDate] = useState('');
  const [error, setError] = useState('');
  const [lastUploadId, setLastUploadId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (token.trim()) {
      localStorage.setItem('adminToken', token.trim());
      setIsAuthenticated(true);
      setError('');
    }
  };

  const logout = () => {
    localStorage.removeItem('adminToken');
    setIsAuthenticated(false);
    setToken('');
  };

  const uploadMutation = useMutation({
    mutationFn: (data: { file: File; newspaperName: string; editionDate: string }) =>
      editionsApi.uploadEdition(data.file, data.newspaperName, data.editionDate),
    onSuccess: (edition) => {
      queryClient.invalidateQueries({ queryKey: ['editions'] });
      setFile(null);
      setNewspaperName('');
      setEditionDate('');
      setLastUploadId(edition.id);
      alert('Edition uploaded successfully! Processing will begin shortly.');
    },
    onError: (error: unknown) => {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const responseDetail = axiosError.response?.data?.detail;
      setError(`Upload failed: ${responseDetail || errorMessage}`);
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError('');
    } else {
      setError('Please select a PDF file');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !newspaperName || !editionDate) {
      setError('Please fill in all fields');
      return;
    }

    const savedToken = localStorage.getItem('adminToken');
    if (savedToken) {
      localStorage.setItem('adminToken', savedToken);
    }

    uploadMutation.mutate({ file, newspaperName, editionDate });
  };

  const { data: lastEdition } = useQuery({
    queryKey: ['edition', lastUploadId],
    queryFn: () => editionsApi.getEdition(lastUploadId as number),
    enabled: lastUploadId !== null,
    refetchInterval: (data) => (data?.status === 'PROCESSING' ? 2000 : false),
  });

  const { data: processingStatus } = useQuery({
    queryKey: ['processing-status', lastUploadId],
    queryFn: () => editionsApi.getProcessingStatus(lastUploadId as number),
    enabled: !!lastEdition && (lastEdition.status === 'PROCESSING' || lastEdition.status === 'FAILED'),
    refetchInterval: lastEdition?.status === 'PROCESSING' ? 2000 : false,
  });

  const processMutation = useMutation({
    mutationFn: () => editionsApi.processEdition(lastUploadId as number),
    onSuccess: () => {
      if (lastUploadId) {
        queryClient.invalidateQueries({ queryKey: ['edition', lastUploadId] });
        queryClient.invalidateQueries({ queryKey: ['processing-status', lastUploadId] });
      }
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
    mutationFn: () => editionsApi.reprocessEdition(lastUploadId as number),
    onSuccess: () => {
      if (lastUploadId) {
        queryClient.invalidateQueries({ queryKey: ['edition', lastUploadId] });
        queryClient.invalidateQueries({ queryKey: ['processing-status', lastUploadId] });
      }
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

  if (!isAuthenticated) {
    return (
      <PageContainer maxWidth="sm">
        <div className="py-12">
          <Card className="p-6">
            <CardHeader>
              <CardTitle className="text-center text-2xl">Admin Login</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleLogin} className="space-y-4">
                <Input
                  label="Admin Token"
                  type="password"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="Enter admin token"
                  required
                />
                <Button type="submit" className="w-full">
                  Login
                </Button>
              </form>
              <p className="mt-4 text-sm text-stone-500 text-center">
                Use the ADMIN_TOKEN from your environment variables
              </p>
            </CardContent>
          </Card>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer maxWidth="2xl">
      <PageHeader
        title="Admin Dashboard"
        actions={
          <Button variant="secondary" onClick={logout}>
            Logout
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>Upload Newspaper Edition</CardTitle>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-ink-800 mb-1.5">
                PDF File
              </label>
              <div className="border-2 border-dashed border-stone-300 rounded-lg p-6 text-center hover:border-stone-400 transition-colors">
                <input
                  type="file"
                  id="file"
                  accept=".pdf"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <label htmlFor="file" className="cursor-pointer">
                  <div className="text-stone-600">
                    {file ? (
                      <span className="text-ink-800 font-medium">{file.name}</span>
                    ) : (
                      <>
                        <span className="text-ink-800 font-medium">Click to upload</span> or drag and drop
                        <div className="text-sm text-stone-500 mt-1">PDF files only</div>
                      </>
                    )}
                  </div>
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

            <Button type="submit" isLoading={uploadMutation.isPending} className="w-full sm:w-auto">
              {uploadMutation.isPending ? 'Uploading...' : 'Upload Edition'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {lastEdition && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Latest Upload</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
              <div>
                <div className="text-lg font-semibold text-ink-800">{lastEdition.newspaper_name}</div>
                <div className="text-sm text-stone-600">
                  Edition: {new Date(lastEdition.edition_date).toLocaleDateString()}
                </div>
                <div className="mt-2">
                  <StatusBadge status={lastEdition.status as 'UPLOADED' | 'PROCESSING' | 'READY' | 'FAILED'} />
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {lastEdition.status === 'UPLOADED' && (
                  <Button onClick={() => processMutation.mutate()} isLoading={processMutation.isPending}>
                    Start Processing
                  </Button>
                )}
                {lastEdition.status === 'READY' && (
                  <Button
                    variant="secondary"
                    onClick={() => reprocessMutation.mutate()}
                    isLoading={reprocessMutation.isPending || processMutation.isPending}
                  >
                    Reprocess
                  </Button>
                )}
                {lastEdition.status === 'FAILED' && (
                  <>
                    <Button onClick={() => processMutation.mutate()} isLoading={processMutation.isPending}>
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

            {lastEdition.status === 'PROCESSING' && (
              <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
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
          </CardContent>
        </Card>
      )}
    </PageContainer>
  );
};

export default Admin;
