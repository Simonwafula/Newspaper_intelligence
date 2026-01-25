import React, { useState, useEffect } from 'react';
import { favoritesApi } from '../services/api';
import { Favorite } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Spinner } from '../components/ui/Spinner';
import { Link } from 'react-router-dom';

const FavoritesPage: React.FC = () => {
    const [favorites, setFavorites] = useState<Favorite[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadFavorites = async () => {
        try {
            setLoading(true);
            const data = await favoritesApi.getFavorites();
            setFavorites(data);
        } catch (err) {
            setError('Failed to load favorites');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadFavorites();
    }, []);

    const handleRemoveFavorite = async (id: number) => {
        try {
            await favoritesApi.removeFavorite(id);
            setFavorites(favorites.filter(f => f.id !== id));
        } catch (err) {
            console.error('Failed to remove favorite', err);
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <Spinner />
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-8">My Favorites</h1>

            {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
                    {error}
                </div>
            )}

            {favorites.length === 0 ? (
                <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
                    <p className="text-gray-500 mb-4 text-lg">You haven't added any favorites yet.</p>
                    <Link to="/search">
                        <Button className="bg-blue-600 hover:bg-blue-700 text-white">
                            Browse Articles
                        </Button>
                    </Link>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {favorites.map((favorite) => (
                        <Card key={favorite.id} className="flex flex-col h-full bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                            <div className="flex-1 p-5">
                                <div className="flex justify-between items-start mb-2">
                                    <span className="text-xs font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wider">
                                        {favorite.item?.item_type}
                                    </span>
                                    <button
                                        onClick={() => handleRemoveFavorite(favorite.id)}
                                        className="text-gray-400 hover:text-red-500 transition-colors"
                                        title="Remove from favorites"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 fill-current text-red-500" viewBox="0 0 20 20">
                                            <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z" />
                                        </svg>
                                    </button>
                                </div>

                                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3 line-clamp-2">
                                    {favorite.item?.title || 'Untitled Item'}
                                </h3>

                                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-4">
                                    {favorite.item?.text}
                                </p>

                                {favorite.notes && (
                                    <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded border border-yellow-100 dark:border-yellow-900/30">
                                        <p className="text-xs font-medium text-yellow-800 dark:text-yellow-400 mb-1 italic">Personal Note:</p>
                                        <p className="text-xs text-yellow-700 dark:text-yellow-500">{favorite.notes}</p>
                                    </div>
                                )}
                            </div>

                            <div className="px-5 py-4 border-t border-gray-100 dark:border-gray-700 mt-auto flex justify-between items-center text-xs text-gray-500">
                                <span>Page {favorite.item?.page_number}</span>
                                <Link
                                    to={`/app/editions/${favorite.item?.edition_id}`}
                                    className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
                                >
                                    View Edition
                                </Link>
                            </div>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
};

export default FavoritesPage;
