import React, { useState, useEffect } from 'react';
import { analyticsApi } from '../services/api';
import { TrendDashboardResponse } from '../types';
import { Card } from '../components/ui/Card';
import { Spinner } from '../components/ui/Spinner';

const TrendsDashboard: React.FC = () => {
    const [data, setData] = useState<TrendDashboardResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [days, setDays] = useState(30);

    const loadTrends = async () => {
        try {
            setLoading(true);
            const result = await analyticsApi.getTrends(days);
            setData(result);
        } catch (err) {
            setError('Failed to load trend data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadTrends();
    }, [days]);

    if (loading && !data) {
        return (
            <div className="flex justify-center items-center h-64">
                <Spinner />
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto px-4 py-8">
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Intelligence Trends</h1>
                <div className="flex items-center space-x-2">
                    <span className="text-sm text-gray-500">Timeframe:</span>
                    <select
                        value={days}
                        onChange={(e) => setDays(parseInt(e.target.value))}
                        className="border border-gray-300 rounded-md px-2 py-1 text-sm bg-white"
                    >
                        <option value={7}>Last 7 Days</option>
                        <option value={30}>Last 30 Days</option>
                        <option value={90}>Last 90 Days</option>
                    </select>
                </div>
            </div>

            {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
                    {error}
                </div>
            )}

            {data && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Top Categories */}
                    <Card className="p-6">
                        <h2 className="text-xl font-bold mb-4 text-gray-800">Top Topic Categories</h2>
                        <div className="space-y-4">
                            {data.top_categories.map((cat, i) => (
                                <div key={cat.name} className="flex flex-col">
                                    <div className="flex justify-between mb-1">
                                        <span className="text-sm font-medium">{cat.name}</span>
                                        <span className="text-sm text-gray-500">{cat.count} items</span>
                                    </div>
                                    <div className="w-full bg-gray-100 rounded-full h-2">
                                        <div
                                            className={`h-2 rounded-full ${['bg-blue-500', 'bg-emerald-500', 'bg-amber-500', 'bg-purple-500', 'bg-rose-500'][i % 5]}`}
                                            style={{ width: `${(cat.count / data.top_categories[0].count) * 100}%` }}
                                        />
                                    </div>
                                </div>
                            ))}
                            {data.top_categories.length === 0 && (
                                <p className="text-gray-500 text-center py-4">No topic data available.</p>
                            )}
                        </div>
                    </Card>

                    {/* Volume Summary */}
                    <Card className="p-6">
                        <h2 className="text-xl font-bold mb-4 text-gray-800">Processing Volume</h2>
                        <div className="flex items-end justify-between h-48 px-2">
                            {data.volume_trends.slice(-14).map((day) => (
                                <div key={day.date} className="flex flex-col items-center flex-1 group" title={`${new Date(day.date).toLocaleDateString()}: ${day.count} items`}>
                                    <div
                                        className="w-4 bg-blue-100 group-hover:bg-blue-300 transition-colors rounded-t pointer-events-none"
                                        style={{ height: `${Math.max((day.count / Math.max(...data.volume_trends.map(d => d.count), 1)) * 100, 5)}%` }}
                                    ></div>
                                    <span className="text-[8px] text-gray-400 mt-1 origin-center rotate-45 md:rotate-0">
                                        {new Date(day.date).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}
                                    </span>
                                </div>
                            ))}
                            {data.volume_trends.length === 0 && (
                                <p className="text-gray-500 text-center w-full py-4">No volume data available.</p>
                            )}
                        </div>
                    </Card>

                    {/* Topic distribution chart area could go here */}
                    <Card className="lg:col-span-2 p-6">
                        <h2 className="text-xl font-bold mb-4 text-gray-800">Trends Insight</h2>
                        <p className="text-gray-600">
                            The dashboard above shows real-time extraction metrics. Currently, the system is tracking {data.top_categories.length} major topics
                            across {data.volume_trends.length} active publication days.
                            {data.top_categories.length > 0 && ` "${data.top_categories[0].name}" remains the most frequent topic.`}
                        </p>
                    </Card>
                </div>
            )}
        </div>
    );
};

export default TrendsDashboard;
