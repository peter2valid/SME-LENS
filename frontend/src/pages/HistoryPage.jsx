import React, { useEffect, useState } from 'react';
import api from '../services/api';
import { Search, Download, Eye } from 'lucide-react';

const HistoryPage = () => {
    // ... state ...
    const [docs, setDocs] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDocs = async () => {
            try {
                const res = await api.get('/upload/');
                setDocs(res.data);
            } catch (error) {
                console.error(error);
            } finally {
                setLoading(false);
            }
        };
        fetchDocs();
    }, []);

    if (loading) return <div className="text-center mt-20 text-muted animate-pulse">Loading history...</div>;

    return (
        <div className="space-y-8">
            <div className="flex justify-between items-center">
                <h2 className="text-3xl font-black text-gradient tracking-tight">Scan History</h2>
                <div className="relative group">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted group-hover:text-primary transition-colors" />
                    <input
                        type="text"
                        placeholder="Search invoices..."
                        className="pl-10 pr-4 py-2 bg-surface border border-border rounded-xl focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 w-64 text-sm transition-all text-text placeholder:text-muted"
                    />
                </div>
            </div>

            <div className="glass-panel overflow-hidden">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="border-b border-border text-muted text-xs bg-primary/5 uppercase tracking-wider font-bold">
                            <th className="p-5">File Name</th>
                            <th className="p-5">Date Scanned</th>
                            <th className="p-5">Vendor</th>
                            <th className="p-5">Total</th>
                            <th className="p-5">Status</th>
                            <th className="p-5 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {docs.map((doc) => (
                            <tr key={doc.id} className="border-b border-border hover:bg-primary/5 transition-colors group">
                                <td className="p-5 font-medium text-text">{doc.filename}</td>
                                <td className="p-5 text-muted text-sm">{new Date(doc.upload_date).toLocaleDateString()}</td>
                                <td className="p-5 font-bold text-text">{doc.ocr_result?.extracted_data?.vendor || "-"}</td>
                                <td className="p-5 text-primary font-mono font-bold">
                                    {doc.ocr_result?.extracted_data?.total ? `$${doc.ocr_result.extracted_data.total}` : "-"}
                                </td>
                                <td className="p-5">
                                    <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider border ${doc.status === 'completed' ? 'bg-success/10 text-success border-success/20' : 'bg-danger/10 text-danger border-danger/20'
                                        }`}>
                                        {doc.status}
                                    </span>
                                </td>
                                <td className="p-5 text-right">
                                    <button className="text-muted hover:text-primary transition-colors p-2 hover:bg-primary/10 rounded-lg">
                                        <Eye className="w-4 h-4" />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {docs.length === 0 && (
                    <div className="p-12 text-center text-muted">
                        No documents found. <span className="text-primary cursor-pointer hover:underline">Upload one now.</span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default HistoryPage;
