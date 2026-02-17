import React, { useState, useEffect } from 'react';
import PDFViewer from './components/PDFViewer';
import DataSidebar from './components/DataSidebar';
import { AlertTriangle, Upload, Loader2 } from 'lucide-react';

function App() {
    const [activeBox, setActiveBox] = useState(null);
    const [data, setData] = useState(null);
    const [pdfUrl, setPdfUrl] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        if (!file.type.includes('pdf')) {
            setError('Please upload a PDF file');
            return;
        }

        setLoading(true);
        setError(null);
        setData(null);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('http://localhost:8000/upload', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const result = await response.json();
            
            // Set the PDF URL from the backend
            setPdfUrl(`http://localhost:8000/uploads/${result.filename}`);
            
            // Set the data with verified_data
            setData({
                ...result,
                verified_data: result.verified_data,
                vision_map: result.vision_map,
            });
            
        } catch (err) {
            console.error('Upload error:', err);
            setError(err.message || 'Failed to upload and process PDF');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex h-screen w-screen bg-gray-900 text-white font-sans overflow-hidden">
            {/* Main Content Area */}
            <div className="flex-1 flex flex-col relative">
                <header className="h-14 bg-gray-800 border-b border-gray-700 flex items-center px-4 justify-between z-20">
                    <h1 className="font-bold text-lg tracking-tight">
                        ResearchOS V3 <span className="text-blue-400 text-xs uppercase ml-2 bg-blue-900/30 px-2 py-1 rounded">Truth Engine</span>
                    </h1>
                    
                    <div className="flex items-center gap-4">
                        <label className="cursor-pointer bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors">
                            <Upload className="w-4 h-4" />
                            <span className="text-sm font-medium">Upload PDF</span>
                            <input
                                type="file"
                                accept=".pdf"
                                onChange={handleFileUpload}
                                className="hidden"
                                disabled={loading}
                            />
                        </label>
                        <div className="text-xs text-gray-400">21 CFR Part 11 Mode: ACTIVE</div>
                    </div>
                </header>

                <div className="flex-1 relative z-10">
                    {loading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 z-30">
                            <div className="text-center">
                                <Loader2 className="w-12 h-12 text-blue-400 animate-spin mx-auto mb-4" />
                                <p className="text-white text-lg">Processing PDF...</p>
                                <p className="text-gray-400 text-sm mt-2">Running Truth Engine pipeline</p>
                            </div>
                        </div>
                    )}
                    
                    {error && (
                        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 z-30">
                            <div className="bg-red-900/50 border border-red-500 rounded-lg p-6 max-w-md">
                                <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-3" />
                                <p className="text-white text-center">{error}</p>
                                <button
                                    onClick={() => setError(null)}
                                    className="mt-4 w-full bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
                                >
                                    Dismiss
                                </button>
                            </div>
                        </div>
                    )}
                    
                    {!pdfUrl && !loading && !error && (
                        <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                            <div className="text-center">
                                <Upload className="w-16 h-16 mx-auto mb-4 opacity-50" />
                                <p className="text-lg">Upload a PDF to begin analysis</p>
                            </div>
                        </div>
                    )}
                    
                    {pdfUrl && (
                        <PDFViewer
                            pdfUrl={pdfUrl}
                            activeBox={activeBox}
                        />
                    )}
                </div>
            </div>

            {/* Sidebar */}
            <div className="z-20 shadow-2xl">
                <DataSidebar
                    data={data}
                    onSelectField={(bbox) => setActiveBox(bbox)}
                />
            </div>
        </div>
    );
}

export default App;
