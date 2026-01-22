import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { editionsApi } from '../services/api';

const Admin: React.FC = () => {
  const [token, setToken] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [newspaperName, setNewspaperName] = useState('');
  const [editionDate, setEditionDate] = useState('');
  const [error, setError] = useState('');
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
      setError(`Upload failed: ${responseDetail || errorMessage}`);
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
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

  if (!isAuthenticated) {
    return (
      <div className="admin-login">
        <h1>Admin Login</h1>
        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label htmlFor="token">Admin Token:</label>
            <input
              type="password"
              id="token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Enter admin token"
              required
            />
          </div>
          <button type="submit" className="btn">Login</button>
        </form>
        <p className="hint">Use the ADMIN_TOKEN from your environment variables</p>
      </div>
    );
  }

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>Admin Dashboard</h1>
        <button onClick={logout} className="btn btn-secondary">Logout</button>
      </div>

      <div className="upload-form">
        <h2>Upload Newspaper Edition</h2>
        {error && <div className="error-message">{error}</div>}
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
    </div>
  );
};

export default Admin;