import React, { useState, useEffect } from 'react';
import { collectionsApi } from '../services/api';
import { Collection, CollectionCreate } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Spinner } from '../components/ui/Spinner';
import { Link } from 'react-router-dom';

const CollectionsPage: React.FC = () => {
    const [collections, setCollections] = useState<Collection[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isCreating, setIsCreating] = useState(false);
    const [formData, setFormData] = useState<CollectionCreate>({
        name: '',
        description: '',
        color: '#3B82F6',
    });

    const loadCollections = async () => {
        try {
            setLoading(true);
            const data = await collectionsApi.getCollections();
            setCollections(data);
        } catch (err) {
            setError('Failed to load collections');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadCollections();
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await collectionsApi.createCollection(formData);
            setFormData({ name: '', description: '', color: '#3B82F6' });
            setIsCreating(false);
            loadCollections();
        } catch (err) {
            setError('Failed to create collection');
            console.error(err);
        }
    };

    if (loading && collections.length === 0) {
        return (
            <div className="flex justify-center items-center h-64">
                <Spinner />
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto px-4 py-8">
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-3xl font-bold text-gray-900">My Collections</h1>
                <Button
                    onClick={() => setIsCreating(true)}
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                    New Collection
                </Button>
            </div>

            {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
                    {error}
                </div>
            )}

            {isCreating && (
                <Card className="mb-8 p-6 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 shadow-lg">
                    <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">Create New Collection</h2>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Collection Name *</label>
                            <Input
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                placeholder="e.g., Labor Market Trends 2024"
                                required
                                className="w-full"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                            <textarea
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                                rows={3}
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                placeholder="What is this collection for?"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Accent Color</label>
                            <input
                                type="color"
                                value={formData.color}
                                onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                                className="h-10 w-20 border border-gray-300 rounded"
                            />
                        </div>
                        <div className="flex justify-end space-x-3">
                            <Button type="button" onClick={() => setIsCreating(false)} className="bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600">
                                Cancel
                            </Button>
                            <Button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white">
                                Create Collection
                            </Button>
                        </div>
                    </form>
                </Card>
            )}

            {collections.length === 0 ? (
                <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                    <p className="text-gray-500 dark:text-gray-400 mb-4">You haven't created any collections yet.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {collections.map((collection) => (
                        <Link key={collection.id} to={`/app/collections/${collection.id}`}>
                            <Card className="h-full hover:border-blue-500 transition-colors border-2 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700" style={{ borderLeftColor: collection.color, borderLeftWidth: '6px' }}>
                                <div className="p-5">
                                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">{collection.name}</h3>
                                    <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">{collection.description || 'No description provided.'}</p>
                                    <div className="mt-4 flex items-center text-xs text-gray-500">
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                        </svg>
                                        Created {new Date(collection.created_at).toLocaleDateString()}
                                    </div>
                                </div>
                            </Card>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
};

export default CollectionsPage;
