import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { motion } from 'framer-motion';

const Auth = () => {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        try {
            if (isLogin) {
                const formData = new FormData();
                formData.append('username', email);
                formData.append('password', password);
                const res = await api.post('/auth/login', formData);
                localStorage.setItem('token', res.data.access_token);
                navigate('/dashboard');
            } else {
                await api.post('/auth/signup', { email, password });
                // Auto login after signup or ask to login
                setIsLogin(true);
                alert("Account created! Please login.");
            }
        } catch (err) {
            setError(err.response?.data?.detail || "An error occurred");
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-background relative overflow-hidden">
            {/* Background glow */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-primary/20 rounded-full blur-[100px]" />

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-md p-8 bg-surface/50 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl relative z-10"
            >
                <h2 className="text-3xl font-bold text-center mb-8 bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                    {isLogin ? 'Welcome Back' : 'Join SMELens'}
                </h2>

                {error && (
                    <div className="mb-4 p-3 bg-danger/10 border border-danger/20 text-danger rounded-lg text-sm text-center">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-400 mb-2">Email</label>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full px-4 py-3 bg-background/50 border border-white/10 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-white placeholder-gray-600"
                            placeholder="you@example.com"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-400 mb-2">Password</label>
                        <input
                            type="password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full px-4 py-3 bg-background/50 border border-white/10 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-white placeholder-gray-600"
                            placeholder="••••••••"
                        />
                    </div>

                    <button
                        type="submit"
                        className="w-full py-3 px-4 bg-gradient-to-r from-primary to-secondary hover:from-primary/90 hover:to-secondary/90 text-white font-medium rounded-lg shadow-lg shadow-primary/25 transition-all transform hover:scale-[1.02]"
                    >
                        {isLogin ? 'Sign In' : 'Create Account'}
                    </button>
                </form>

                <div className="mt-6 text-center text-sm text-gray-400">
                    <button
                        onClick={() => setIsLogin(!isLogin)}
                        className="hover:text-white underline decoration-dashed underline-offset-4 transition-colors"
                    >
                        {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
                    </button>
                </div>
            </motion.div>
        </div>
    );
};

export default Auth;
