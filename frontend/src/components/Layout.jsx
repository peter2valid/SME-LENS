import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { LogOut, LayoutDashboard, History, PlusCircle } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import { Dock } from './Dock';
import api from '../services/api';

const Layout = ({ children }) => {
    const location = useLocation();
    const [recentDocs, setRecentDocs] = useState([]);
    const [showDock, setShowDock] = useState(true);

    // Fetch recent docs for folder preview
    useEffect(() => {
        const fetchRecentDocs = async () => {
            try {
                const res = await api.get('/upload/');
                const docs = res.data.slice(0, 5).map(doc => ({
                    id: doc.id,
                    vendor: doc.ocr_result?.extracted_data?.vendor || 'Document',
                    total: doc.ocr_result?.extracted_data?.total_amount || doc.ocr_result?.extracted_data?.total
                }));
                setRecentDocs(docs);
            } catch (error) {
                console.error('Failed to fetch recent docs', error);
            }
        };
        fetchRecentDocs();
    }, []);

    // Hide dock on upload page (has its own UI)
    useEffect(() => {
        setShowDock(!location.pathname.includes('/upload'));
    }, [location]);

    return (
        <div className="min-h-screen bg-background text-text font-sans selection:bg-primary/30">
            {/* Navbar */}
            <nav className="fixed top-0 w-full z-50 border-b border-border bg-surface/80 backdrop-blur-md shadow-lg shadow-black/20">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <div className="flex items-center">
                            <Link to="/dashboard" className="text-2xl font-bold text-gradient hover:opacity-80 transition-opacity font-display">
                                SMELens
                            </Link>
                        </div>
                        <div className="flex items-center space-x-4">
                            <ThemeToggle />
                            <Link to="/upload" className="btn-primary shadow-glow-primary">
                                <PlusCircle className="w-4 h-4 mr-2" />
                                New Scan
                            </Link>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Sidebar + Content */}
            <div className="flex pt-16">
                {/* Simple Sidebar for desktop */}
                <aside className="hidden lg:block w-64 fixed h-full border-r border-border bg-surface/30 backdrop-blur-sm">
                    <div className="p-4 space-y-2">
                        <Link to="/dashboard" className="flex items-center px-4 py-3 rounded-lg hover:bg-primary/10 text-muted hover:text-text transition-all hover:translate-x-1 duration-200">
                            <LayoutDashboard className="w-5 h-5 mr-3" />
                            Dashboard
                        </Link>
                        <Link to="/history" className="flex items-center px-4 py-3 rounded-lg hover:bg-primary/10 text-muted hover:text-text transition-all hover:translate-x-1 duration-200">
                            <History className="w-5 h-5 mr-3" />
                            History
                        </Link>
                    </div>
                </aside>

                {/* Main Content - add padding for dock on mobile */}
                <main className="flex-1 lg:ml-64 p-6 pb-32 lg:pb-6 overflow-y-auto">
                    <div className="max-w-7xl mx-auto">
                        {children}
                    </div>
                </main>
            </div>

            {/* Mobile Dock - only visible on smaller screens */}
            <div className="lg:hidden">
                <Dock recentDocs={recentDocs} visible={showDock} />
            </div>
        </div>
    );
};

export default Layout;
