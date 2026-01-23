import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { collectionsApi } from '../services/api';
import { CollectionWithItems } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Spinner } from '../components/ui/Spinner';

const CollectionDetailPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [collection, setCollection] = useState<CollectionWithItems | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadCollection = useCallback(async () => {
        if (!id) return;
        try {
            setLoading(true);
            const data = await collectionsApi.getCollection(parseInt(id));
            setCollection(data);
        } catch (err) {
            setError('Failed to load collection');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [id]);

    useEffect(() => {
        loadCollection();
    }, [loadCollection]);

    const handleRemoveItem = async (itemId: number) => {
        if (!id || !collection) return;
        try {
            await collectionsApi.removeItemFromCollection(collection.id, itemId);
            setCollection({
                ...collection,
                items: collection.items.filter(item => item.item_id !== itemId)
            });
        } catch (err) {
            console.error('Failed to remove item', err);
        }
    };

    const handleDeleteCollection = async () => {
        if (!id || !collection) return;
        if (!window.confirm('Are you sure you want to delete this collection and all its items?')) return;

        try {
            await collectionsApi.deleteCollection(collection.id);
            navigate('/app/collections');
        } catch (err) {
            console.error('Failed to delete collection', err);
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <Spinner />
            </div>
        );
    }

    if (!collection) {
        return (
            <div className="max-w-6xl mx-auto px-4 py-8 text-center text-gray-500">
                Collection not found.
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto px-4 py-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
                <div className="flex items-center space-x-4">
                    <Link to="/app/collections" className="text-gray-500 hover:text-gray-700 transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                        </svg>
                    </Link>
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 flex items-center">
                            <span className="w-6 h-6 rounded-full mr-3 border" style={{ backgroundColor: collection.color }}></span>
                            {collection.name}
                        </h1>
                        <p className="text-gray-600 mt-1">{collection.description}</p>
                    </div>
                </div>
                <div className="flex space-x-2">
                    <Button onClick={handleDeleteCollection} className="bg-red-50 text-red-600 hover:bg-red-100 border border-red-200">
                        Delete Collection
                    </Button>
                </div>
            </div>

            {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
                    {error}
                </div>
            )}

            {collection.items.length === 0 ? (
                <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
                    <p className="text-gray-500 mb-4 text-lg">This collection is empty.</p>
                    <Link to="/app/search">
                        <Button className="bg-blue-600 hover:bg-blue-700 text-white">
                            Add Items from Search
                        </Button>
                    </Link>
                </div>
            ) : (
                <div className="space-y-6">
                    <h2 className="text-xl font-semibold text-gray-800">{collection.items.length} Items</h2>
                    <div className="grid grid-cols-1 gap-6">
                        {collection.items.map((collectionItem) => (
                            <Card key={collectionItem.id} className="overflow-hidden flex flex-col md:flex-row bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                                <div className="flex-1 p-6">
                                    <div className="flex justify-between items-start mb-4">
                                        <div>
                                            <span className="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-tighter mr-2">
                                                {collectionItem.item?.item_type}
                                            </span>
                                            <span className="text-xs text-gray-400">
                                                Page {collectionItem.item?.page_number} • {new Date(collectionItem.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                        <button
                                            onClick={() => handleRemoveItem(collectionItem.item_id)}
                                            className="text-gray-400 hover:text-red-500 p-1"
                                            title="Remove from collection"
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                                            </svg>
                                        </button>
                                    </div>

                                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
                                        {collectionItem.item?.title || 'Untitled Item'}
                                    </h3>

                                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-6 line-clamp-3">
                                        {collectionItem.item?.text}
                                    </p>

                                    {collectionItem.notes && (
                                        <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-100 dark:border-gray-600">
                                            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Research Notes</h4>
                                            <p className="text-sm text-gray-700 dark:text-white">{collectionItem.notes}</p>
                                        </div>
                                    )}

                                    <div className="mt-6 flex justify-end">
                                        <Link to={`/app/editions/${collectionItem.item?.edition_id}`}>
                                            <Button size="sm" className="bg-gray-100 text-gray-900 hover:bg-gray-200">
                                                Open Edition
                                            </Button>
                                        </Link>
                                    </div>
                                </div>
                            </Card>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default CollectionDetailPage;
