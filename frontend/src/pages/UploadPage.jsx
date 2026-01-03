import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, CheckCircle, AlertCircle, Loader2, Save, Camera, FileImage } from 'lucide-react';
import api from '../services/api';
import CameraScanner from '../components/CameraScanner';

const UploadPage = () => {
    // ... state ...
    const [file, setFile] = useState(null);
    const [preview, setPreview] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [inputMode, setInputMode] = useState('camera'); // 'dropzone' | 'camera'

    const onDrop = useCallback((acceptedFiles) => {
        const file = acceptedFiles[0];
        setFile(file);
        setPreview(URL.createObjectURL(file));
        setResult(null);
        setError(null);
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'image/*': ['.jpeg', '.png', '.jpg'] },
        multiple: false
    });

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await api.post('/upload/', formData);
            setResult(res.data);
        } catch (err) {
            console.error(err);
            setError("Upload failed. Please try again.");
        } finally {
            setUploading(false);
        }
    };

    // Handler for CameraScanner component
    const handleScanComplete = async (scannedFile) => {
        setFile(scannedFile);
        setPreview(URL.createObjectURL(scannedFile));
        setUploading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', scannedFile);

        try {
            const res = await api.post('/upload/', formData);
            setResult(res.data);
        } catch (err) {
            console.error(err);
            setError("Upload failed. Please try again.");
            throw err; // Re-throw so CameraScanner shows error state
        } finally {
            setUploading(false);
        }
    };

    const handleScanError = (err) => {
        setError(err.message || "Camera/scan error occurred.");
    };

    return (
        <div className="max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <h2 className="text-4xl font-black text-gradient tracking-tight">Scan New Document</h2>

                {/* Input Mode Toggle */}
                <div className="flex items-center gap-2 bg-surface rounded-lg p-1 border border-border">
                    <button
                        onClick={() => setInputMode('camera')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                            inputMode === 'camera'
                                ? 'bg-secondary text-white shadow-glow-secondary'
                                : 'text-muted hover:text-text'
                        }`}
                    >
                        <Camera className="w-4 h-4" />
                        Camera
                    </button>
                    <button
                        onClick={() => setInputMode('dropzone')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                            inputMode === 'dropzone'
                                ? 'bg-primary text-white shadow-glow-primary'
                                : 'text-muted hover:text-text'
                        }`}
                    >
                        <FileImage className="w-4 h-4" />
                        Upload
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 min-h-[600px]">
                {/* Upload/Camera Area */}
                <div className="space-y-6 flex flex-col">
                    <AnimatePresence mode="wait">
                        {inputMode === 'camera' ? (
                            <motion.div
                                key="camera"
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 20 }}
                                className="flex-1 glass-card p-6 flex items-center justify-center"
                            >
                                <CameraScanner
                                    onScanComplete={handleScanComplete}
                                    onError={handleScanError}
                                />
                            </motion.div>
                        ) : (
                            <motion.div
                                key="dropzone"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                className="flex-1 flex flex-col space-y-6"
                            >
                                <div
                                    {...getRootProps()}
                                    className={`flex-1 glass-card border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-all relative overflow-hidden group ${isDragActive ? 'border-primary bg-primary/10' : 'border-border hover:border-primary/50'
                                        }`}
                                >
                                    <input {...getInputProps()} />

                                    {preview ? (
                                        <img src={preview} alt="Preview" className="w-full h-full object-contain p-4 group-hover:scale-105 transition-transform duration-500" />
                                    ) : (
                                        <div className="text-center p-6 space-y-4">
                                            <div className="bg-gradient-to-br from-primary to-secondary p-5 rounded-full inline-block shadow-lg shadow-primary/30 group-hover:scale-110 transition-transform">
                                                <UploadCloud className="w-10 h-10 text-white" />
                                            </div>
                                            <div>
                                                <p className="text-xl font-bold text-text">Click or drag receipt here</p>
                                                <p className="text-sm text-muted mt-2">Supports JPG, PNG</p>
                                            </div>
                                        </div>
                                    )}

                                    {/* Scanning Animation overlay */}
                                    {uploading && (
                                        <motion.div
                                            className="absolute inset-0 bg-primary/20 backdrop-blur-sm z-10"
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                        >
                                            <motion.div
                                                className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/50 to-transparent w-full h-20"
                                                initial={{ top: "-20%" }}
                                                animate={{ top: "120%" }}
                                                transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                                            />
                                        </motion.div>
                                    )}
                                </div>

                                <button
                                    onClick={handleUpload}
                                    disabled={!file || uploading}
                                    className={`w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center transition-all shadow-lg ${!file || uploading
                                        ? 'bg-surface border border-border text-muted cursor-not-allowed'
                                        : 'bg-gradient-to-r from-primary to-secondary hover:shadow-primary/50 text-white hover:scale-[1.02]'
                                        }`}
                                >
                                    {uploading ? <><Loader2 className="animate-spin mr-2" /> Processing...</> : 'Extract Text'}
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {error && (
                        <div className="bg-danger/10 border border-danger/50 text-danger p-4 rounded-xl flex items-center">
                            <AlertCircle className="w-5 h-5 mr-3" />
                            {error}
                        </div>
                    )}
                </div>

                {/* Results Area */}
                <div className="glass-panel p-8 h-full overflow-y-auto relative">
                    {!result ? (
                        <div className="flex flex-col items-center justify-center h-full text-muted space-y-4">
                            <div className="w-16 h-16 rounded-full bg-primary/5 flex items-center justify-center">
                                <Save className="w-8 h-8 opacity-30" />
                            </div>
                            <p>Extracted data will appear here...</p>
                        </div>
                    ) : (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="space-y-8"
                        >
                            {/* Header with Type and Confidence */}
                            <div className="flex items-center justify-between border-b border-border pb-6">
                                <div>
                                    <h3 className="text-2xl font-bold text-text flex items-center capitalize">
                                        {result.document_type || "Document"} Detected
                                    </h3>
                                    <p className="text-sm text-muted mt-1 max-w-md">
                                        {result.explanation}
                                    </p>
                                </div>
                                <div className="flex flex-col items-end">
                                    <span className={`text-lg font-black ${
                                        result.confidence > 0.8 ? 'text-success' : 
                                        result.confidence > 0.5 ? 'text-warning' : 'text-danger'
                                    }`}>
                                        {Math.round((result.confidence || 0) * 100)}%
                                    </span>
                                    <span className="text-xs text-muted uppercase tracking-wider">Confidence</span>
                                </div>
                            </div>

                            {/* Dynamic Fields based on Type */}
                            <div className="space-y-6">
                                
                                {/* Receipt / Invoice Fields */}
                                {['receipt', 'invoice', 'unknown'].includes(result.document_type) && (
                                    <>
                                        <div className="bg-primary/5 p-4 rounded-xl border border-border">
                                            <label className="text-xs text-muted uppercase tracking-wider font-bold">Vendor / Business</label>
                                            <p className="text-2xl font-bold text-text mt-1">
                                                {result.extracted_data?.vendor || "Unknown Vendor"}
                                            </p>
                                        </div>

                                        <div className="grid grid-cols-2 gap-6">
                                            <div className="bg-primary/5 p-4 rounded-xl border border-border">
                                                <label className="text-xs text-muted uppercase tracking-wider font-bold">Date</label>
                                                <p className="text-lg font-medium text-text mt-1">
                                                    {result.extracted_data?.date || "N/A"}
                                                </p>
                                            </div>
                                            <div className="bg-primary/10 p-4 rounded-xl border border-primary/20 relative overflow-hidden">
                                                <label className="text-xs text-primary uppercase tracking-wider font-bold relative z-10">Total Amount</label>
                                                <p className="font-black text-3xl text-gradient mt-1 relative z-10">
                                                    {result.extracted_data?.currency || ""} {result.extracted_data?.total_amount || "0.00"}
                                                </p>
                                            </div>
                                        </div>
                                    </>
                                )}

                                {/* Form Fields */}
                                {result.document_type === 'form' && (
                                    <>
                                        <div className="bg-primary/5 p-4 rounded-xl border border-border">
                                            <label className="text-xs text-muted uppercase tracking-wider font-bold">Institution</label>
                                            <p className="text-xl font-bold text-text mt-1">
                                                {result.extracted_data?.institution_name || "Unknown Institution"}
                                            </p>
                                        </div>
                                        
                                        <div className="bg-surface p-4 rounded-xl border border-border">
                                            <label className="text-xs text-muted uppercase tracking-wider font-bold">Form Title</label>
                                            <p className="text-lg font-medium text-text mt-1">
                                                {result.extracted_data?.form_title || "Untitled Form"}
                                            </p>
                                        </div>

                                        {result.extracted_data?.identifiers && Object.entries(result.extracted_data.identifiers).map(([key, value]) => (
                                            <div key={key} className="bg-surface p-4 rounded-xl border border-border flex justify-between items-center">
                                                <label className="text-xs text-muted uppercase tracking-wider font-bold capitalize">{key.replace('_', ' ')}</label>
                                                <p className="text-lg font-mono font-bold text-primary">{value}</p>
                                            </div>
                                        ))}
                                    </>
                                )}

                                {/* Letter Fields */}
                                {result.document_type === 'letter' && (
                                    <>
                                        <div className="bg-primary/5 p-4 rounded-xl border border-border">
                                            <label className="text-xs text-muted uppercase tracking-wider font-bold">Sender</label>
                                            <p className="text-xl font-bold text-text mt-1">
                                                {result.extracted_data?.sender || "Unknown Sender"}
                                            </p>
                                        </div>
                                        
                                        <div className="bg-surface p-4 rounded-xl border border-border">
                                            <label className="text-xs text-muted uppercase tracking-wider font-bold">Subject</label>
                                            <p className="text-lg font-medium text-text mt-1 italic">
                                                {result.extracted_data?.subject || "No Subject"}
                                            </p>
                                        </div>
                                    </>
                                )}

                                {/* Government ID Documents (Birth Certificate, National ID, Passport, etc.) */}
                                {['birth_certificate', 'national_id', 'passport', 'driving_license'].includes(result.document_type) && (
                                    <>
                                        {/* ID Type Badge */}
                                        <div className="flex items-center gap-2 mb-4">
                                            <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-secondary/20 text-secondary border border-secondary/30">
                                                {result.document_type.replace('_', ' ')}
                                            </span>
                                            {result.extracted_data?.issuing_authority && (
                                                <span className="text-xs text-muted">{result.extracted_data.issuing_authority}</span>
                                            )}
                                        </div>

                                        {/* Full Name - Primary Field */}
                                        <div className="bg-gradient-to-r from-primary/10 to-secondary/10 p-5 rounded-xl border border-primary/20">
                                            <label className="text-xs text-primary uppercase tracking-wider font-bold">Full Name</label>
                                            <p className="text-2xl font-black text-text mt-1">
                                                {result.extracted_data?.full_name || "Name not extracted"}
                                            </p>
                                        </div>

                                        {/* ID Number */}
                                        {result.extracted_data?.id_number && (
                                            <div className="bg-surface p-4 rounded-xl border border-border">
                                                <label className="text-xs text-muted uppercase tracking-wider font-bold">Certificate / ID Number</label>
                                                <p className="text-xl font-mono font-bold text-primary mt-1">
                                                    {result.extracted_data.id_number}
                                                </p>
                                            </div>
                                        )}

                                        <div className="grid grid-cols-2 gap-4">
                                            {/* Date of Birth */}
                                            <div className="bg-primary/5 p-4 rounded-xl border border-border">
                                                <label className="text-xs text-muted uppercase tracking-wider font-bold">Date of Birth</label>
                                                <p className="text-lg font-medium text-text mt-1">
                                                    {result.extracted_data?.date_of_birth || result.extracted_data?.date || "N/A"}
                                                </p>
                                            </div>

                                            {/* Place of Birth */}
                                            <div className="bg-primary/5 p-4 rounded-xl border border-border">
                                                <label className="text-xs text-muted uppercase tracking-wider font-bold">Place of Birth</label>
                                                <p className="text-lg font-medium text-text mt-1">
                                                    {result.extracted_data?.place_of_birth || "N/A"}
                                                </p>
                                            </div>
                                        </div>

                                        {/* Parents' Names */}
                                        {(result.extracted_data?.father_name || result.extracted_data?.mother_name) && (
                                            <div className="grid grid-cols-2 gap-4">
                                                {result.extracted_data?.father_name && (
                                                    <div className="bg-surface p-4 rounded-xl border border-border">
                                                        <label className="text-xs text-muted uppercase tracking-wider font-bold">Father's Name</label>
                                                        <p className="text-lg font-medium text-text mt-1">
                                                            {result.extracted_data.father_name}
                                                        </p>
                                                    </div>
                                                )}
                                                {result.extracted_data?.mother_name && (
                                                    <div className="bg-surface p-4 rounded-xl border border-border">
                                                        <label className="text-xs text-muted uppercase tracking-wider font-bold">Mother's Name</label>
                                                        <p className="text-lg font-medium text-text mt-1">
                                                            {result.extracted_data.mother_name}
                                                        </p>
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {/* Other Identifiers */}
                                        {result.extracted_data?.identifiers && Object.keys(result.extracted_data.identifiers).length > 0 && (
                                            <div className="space-y-2">
                                                <label className="text-xs text-muted uppercase tracking-wider font-bold">Other Details</label>
                                                {Object.entries(result.extracted_data.identifiers).map(([key, value]) => (
                                                    <div key={key} className="bg-surface p-3 rounded-lg border border-border flex justify-between items-center">
                                                        <span className="text-xs text-muted capitalize">{key.replace('_', ' ')}</span>
                                                        <span className="text-sm font-mono font-bold text-text">{value}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </>
                                )}

                                {/* Common: Raw Text Toggle */}
                                <div className="pt-6 border-t border-border">
                                    <details className="group">
                                        <summary className="flex items-center justify-between cursor-pointer list-none text-xs text-muted uppercase tracking-wider font-bold mb-3">
                                            <span>Raw Text Preview</span>
                                            <span className="group-open:rotate-180 transition-transform">▼</span>
                                        </summary>
                                        <div className="bg-surface p-4 rounded-xl text-sm text-muted font-mono text-xs max-h-48 overflow-y-auto border border-border whitespace-pre-wrap">
                                            {result.cleaned_text || result.raw_text}
                                        </div>
                                    </details>
                                </div>
                                
                                {/* Debug/Notes */}
                                {result.notes && result.notes.length > 0 && (
                                    <div className="bg-warning/5 border border-warning/20 p-4 rounded-xl">
                                        <label className="text-xs text-warning uppercase tracking-wider font-bold mb-2 block">System Notes</label>
                                        <ul className="list-disc list-inside text-xs text-muted space-y-1">
                                            {result.notes.map((note, i) => (
                                                <li key={i}>{note}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default UploadPage;
