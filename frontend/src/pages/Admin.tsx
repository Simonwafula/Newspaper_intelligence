import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { editionsApi, usersApi } from '../services/api';
import { PageContainer, PageHeader } from '../components/layout';
import { Button, Input, Card, CardHeader, CardTitle, CardContent, StatusBadge } from '../components/ui';
import { User, UserRole } from '../types';

const Admin = () => {
  const [activeTab, setActiveTab] = useState<'uploads' | 'users'>('uploads');
  const [file, setFile] = useState<File | null>(null);
  const [newspaperName, setNewspaperName] = useState('');
  const [editionDate, setEditionDate] = useState('');
  const [error, setError] = useState('');
  const [lastUploadId, setLastUploadId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  // User Management State
  const [newUserName, setNewUserName] = useState('');
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [newUserRole, setNewUserRole] = useState<UserRole>('READER');

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

  const { data: users, isLoading: usersLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => usersApi.getUsers(),
    enabled: activeTab === 'users',
  });

  const createUserMutation = useMutation({
    mutationFn: (data: Partial<User> & { password?: string }) => usersApi.createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setNewUserName('');
      setNewUserEmail('');
      setNewUserPassword('');
      setNewUserRole('READER');
      alert('User created successfully!');
    },
    onError: (error: any) => {
      alert(`Failed to create user: ${error.response?.data?.detail || error.message}`);
    },
  });

  const deleteUserMutation = useMutation({
    mutationFn: (userId: number) => usersApi.deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      alert('User deactivated successfully!');
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

    uploadMutation.mutate({ file, newspaperName, editionDate });
  };

  const handleCreateUser = (e: React.FormEvent) => {
    e.preventDefault();
    createUserMutation.mutate({
      full_name: newUserName,
      email: newUserEmail,
      password: newUserPassword,
      role: newUserRole,
    });
  };

  const { data: lastEdition } = useQuery({
    queryKey: ['edition', lastUploadId],
    queryFn: () => editionsApi.getEdition(lastUploadId as number),
    enabled: lastUploadId !== null,
    refetchInterval: (query) => (query.state.data?.status === 'PROCESSING' ? 2000 : false),
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

  return (
    <PageContainer maxWidth="4xl">
      <PageHeader title="Admin Dashboard" />

      <div className="flex gap-4 mb-6 border-b border-stone-200">
        <button
          className={`pb-2 px-1 text-sm font-medium transition-colors ${activeTab === 'uploads'
              ? 'border-b-2 border-ink-800 text-ink-800'
              : 'text-stone-500 hover:text-stone-700'
            }`}
          onClick={() => setActiveTab('uploads')}
        >
          Newspaper Uploads
        </button>
        <button
          className={`pb-2 px-1 text-sm font-medium transition-colors ${activeTab === 'users'
              ? 'border-b-2 border-ink-800 text-ink-800'
              : 'text-stone-500 hover:text-stone-700'
            }`}
          onClick={() => setActiveTab('users')}
        >
          User Management
        </button>
      </div>

      {activeTab === 'uploads' ? (
        <div className="max-w-2xl">
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
                      <StatusBadge status={lastEdition.status as any} />
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
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>System Users</CardTitle>
              </CardHeader>
              <CardContent>
                {usersLoading ? (
                  <div className="text-center py-8 text-stone-500 text-sm">Loading users...</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-stone-200">
                          <th className="py-3 font-semibold text-ink-800">User</th>
                          <th className="py-3 font-semibold text-ink-800">Role</th>
                          <th className="py-3 font-semibold text-ink-800">Status</th>
                          <th className="py-3 font-semibold text-ink-800">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-stone-100">
                        {users?.map((user) => (
                          <tr key={user.id}>
                            <td className="py-3">
                              <div className="font-medium text-ink-800">{user.full_name}</div>
                              <div className="text-stone-500 text-xs">{user.email}</div>
                            </td>
                            <td className="py-3">
                              <select
                                value={user.role}
                                onChange={(e) => usersApi.updateUserRole(user.id, e.target.value as UserRole).then(() => queryClient.invalidateQueries({ queryKey: ['users'] }))}
                                className="bg-white border border-stone-200 rounded px-2 py-1 text-xs font-semibold text-ink-800 focus:outline-none focus:ring-1 focus:ring-ink-800"
                              >
                                <option value="READER">Reader</option>
                                <option value="EDITOR">Editor</option>
                                <option value="ADMIN">Admin</option>
                              </select>
                            </td>
                            <td className="py-3">
                              {user.is_active ? (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                  Active
                                </span>
                              ) : (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-stone-100 text-stone-800">
                                  Inactive
                                </span>
                              )}
                            </td>
                            <td className="py-3">
                              {user.is_active && (
                                <button
                                  onClick={() => {
                                    if (window.confirm(`Are you sure you want to deactivate ${user.full_name}?`)) {
                                      deleteUserMutation.mutate(user.id);
                                    }
                                  }}
                                  className="text-red-600 hover:text-red-700 font-medium"
                                  disabled={user.role === 'ADMIN' && users.filter(u => u.role === 'ADMIN').length === 1}
                                >
                                  Deactivate
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div>
            <Card>
              <CardHeader>
                <CardTitle>Add New User</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateUser} className="space-y-4">
                  <Input
                    label="Full Name"
                    value={newUserName}
                    onChange={(e) => setNewUserName(e.target.value)}
                    required
                  />
                  <Input
                    label="Email"
                    type="email"
                    value={newUserEmail}
                    onChange={(e) => setNewUserEmail(e.target.value)}
                    required
                  />
                  <Input
                    label="Initial Password"
                    type="password"
                    value={newUserPassword}
                    onChange={(e) => setNewUserPassword(e.target.value)}
                    required
                    description="Minimum 8 characters"
                  />
                  <div>
                    <label className="block text-sm font-medium text-ink-800 mb-1.5">Role</label>
                    <select
                      value={newUserRole}
                      onChange={(e) => setNewUserRole(e.target.value as UserRole)}
                      className="w-full px-3 py-2 bg-white border border-stone-300 rounded-lg text-ink-800 focus:outline-none focus:ring-2 focus:ring-ink-800 font-medium"
                    >
                      <option value="READER">Reader</option>
                      <option value="EDITOR">Editor</option>
                      <option value="ADMIN">Admin</option>
                    </select>
                  </div>
                  <Button
                    type="submit"
                    className="w-full"
                    isLoading={createUserMutation.isPending}
                  >
                    Create User
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </PageContainer>
  );
};

export default Admin;
