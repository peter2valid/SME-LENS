import React, { useEffect, useState } from 'react';
import api from '../services/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { FileText, DollarSign, Activity, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

const Dashboard = () => {
    const [stats, setStats] = useState({ totalDocs: 0, totalAmount: 0, recentDocs: [] });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await api.get('/upload/');
                const docs = res.data;
                const totalAmount = docs.reduce((sum, doc) => {
                    // Support both enterprise (total_amount) and legacy (total) format
                    const amount = doc.ocr_result?.extracted_data?.total_amount 
                        || doc.ocr_result?.extracted_data?.total 
                        || 0;
                    return sum + parseFloat(amount);
                }, 0);

                setStats({
                    totalDocs: docs.length,
                    totalAmount: totalAmount,
                    recentDocs: docs.slice(0, 5)
                });
            } catch (error) {
                console.error("Failed to fetch dashboard data", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const data = [
        { name: 'Jan', amt: 2400 },
        { name: 'Feb', amt: 1398 },
        { name: 'Mar', amt: 9800 },
        { name: 'Apr', amt: 3908 },
        { name: 'May', amt: 4800 },
        { name: 'Jun', amt: 3800 },
    ];

    if (loading) {
        return <div className="text-center mt-20 text-gray-400 animate-pulse">Loading dashboard...</div>;
    }

    return (
        <div className="space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Stat Cards */}
                <div className="glass-card p-6 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-110 transition-transform duration-500">
                        <FileText className="w-32 h-32 text-primary" />
                    </div>
                    <h3 className="text-muted text-sm font-medium uppercase tracking-wider">Total Documents</h3>
                    <p className="text-4xl font-black mt-2 text-text">{stats.totalDocs}</p>
                    <div className="mt-4 flex items-center text-sm text-success">
                        <Activity className="w-4 h-4 mr-1" /> +12% from last month
                    </div>
                </div>

                <div className="glass-card p-6 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-110 transition-transform duration-500">
                        <DollarSign className="w-32 h-32 text-secondary" />
                    </div>
                    <h3 className="text-muted text-sm font-medium uppercase tracking-wider">Total Processed</h3>
                    <p className="text-4xl font-black mt-2 text-text">${stats.totalAmount.toFixed(2)}</p>
                    <div className="mt-4 flex items-center text-sm text-success">
                        <Activity className="w-4 h-4 mr-1" /> +8% from last month
                    </div>
                </div>

                <div className="glass-card p-8 bg-gradient-to-br from-primary/20 to-secondary/20 border-primary/20 flex flex-col justify-center items-start">
                    <h3 className="text-2xl font-bold mb-2 text-text">Ready to scan?</h3>
                    <p className="text-muted text-sm mb-6">Upload new invoices instantly.</p>
                    <Link to="/upload" className="btn-primary">
                        Start Upload <ChevronRight className="w-4 h-4 ml-1" />
                    </Link>
                </div>
            </div>

            {/* Charts & Recent List */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="glass-panel p-6">
                    <h3 className="text-lg font-bold mb-6 text-gradient">Expense Trend</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={data}>
                                <XAxis dataKey="name" stroke="currentColor" className="text-muted" fontSize={12} tickLine={false} axisLine={false} />
                                <YAxis stroke="currentColor" className="text-muted" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `$${value}`} />
                                <Tooltip
                                    cursor={{ fill: 'rgba(79, 70, 229, 0.1)' }}
                                    contentStyle={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                                    itemStyle={{ color: 'var(--color-text)' }}
                                    labelStyle={{ color: 'var(--color-text)' }}
                                />
                                <Bar dataKey="amt" fill="#4F46E5" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="glass-panel p-6">
                    <div className="flex justify-between items-center mb-6">
                        <h3 className="text-lg font-bold text-gradient">Recent Uploads</h3>
                        <Link to="/history" className="text-sm text-primary hover:text-accent transition-colors">View All</Link>
                    </div>

                    <div className="space-y-4">
                        {stats.recentDocs.length === 0 ? (
                            <div className="text-center py-8">
                                <FileText className="w-12 h-12 text-muted mx-auto mb-3 opacity-50" />
                                <p className="text-muted">No documents yet.</p>
                            </div>
                        ) : (
                            stats.recentDocs.map((doc) => {
                                const vendor = doc.ocr_result?.extracted_data?.vendor || "Unknown";
                                // Support both enterprise (total_amount) and legacy (total) format
                                const totalVal = doc.ocr_result?.extracted_data?.total_amount 
                                    || doc.ocr_result?.extracted_data?.total;
                                const total = totalVal
                                    ? `$${parseFloat(totalVal).toFixed(2)}`
                                    : "N/A";

                                return (
                                    <div key={doc.id} className="group flex items-center justify-between p-3 rounded-lg hover:bg-primary/5 transition-colors border border-transparent hover:border-primary/10">
                                        <div className="flex items-center">
                                            <div className="p-3 bg-primary/10 rounded-xl text-primary group-hover:bg-primary/20 group-hover:scale-105 transition-all mr-4">
                                                <FileText className="w-5 h-5" />
                                            </div>
                                            <div>
                                                <p className="font-bold text-text text-sm">{vendor}</p>
                                                <p className="text-xs text-muted">{new Date(doc.upload_date).toLocaleDateString()}</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="font-bold text-text mb-1">{total}</p>
                                            <span className={`inline-block px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded ${doc.status === 'completed' ? 'bg-success/20 text-success' :
                                                doc.status === 'failed' ? 'bg-danger/20 text-danger' : 'bg-primary/20 text-primary'
                                                }`}>
                                                {doc.status}
                                            </span>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
