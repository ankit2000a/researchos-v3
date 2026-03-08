import React, { useState, useEffect } from 'react';
import PDFViewer from './components/PDFViewer';
import DataSidebar from './components/DataSidebar';

const PDF_URL = null;

function App() {
    const pdfViewerRef = React.useRef(null);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadedFile, setUploadedFile] = useState(null);
    const [pdfUrl, setPdfUrl] = useState(PDF_URL);

    // DEBUG: Monitor data state changes
    useEffect(() => {
        if (data) console.log('🔄 App state updated with data:', data);
    }, [data]);

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        setIsUploading(true);
        setError(null);
        setData(null);

        try {
            // Upload file
            const formData = new FormData();
            formData.append('file', file);

            const uploadResponse = await fetch('http://localhost:8000/upload', {
                method: 'POST',
                body: formData,
            });

            if (!uploadResponse.ok) throw new Error('Upload failed');
            const uploadData = await uploadResponse.json();

            // Process the uploaded file
            const processResponse = await fetch(`http://localhost:8000/process/${uploadData.session_id}`);
            if (!processResponse.ok) throw new Error('Processing failed');
            const results = await processResponse.json();

            console.log('📦 Results data:', results);

            // Update state with results
            // Update state with results - Force new object reference
            setUploadedFile(file.name);
            setData({ ...results });

            // Update PDF viewer
            setPdfUrl(URL.createObjectURL(file));

        } catch (error) {
            console.error('Upload failed:', error);
            setError(error.message || 'Failed to analyze PDF.');
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="flex flex-col h-screen overflow-hidden bg-gray-900 text-white font-sans">
            {/* Header - Fixed Height */}
            <header className="h-16 bg-gray-800 border-b border-gray-700 flex items-center px-6 justify-between shrink-0 z-20">
                <div className="flex items-center gap-4">
                    <h1 className="font-bold text-xl tracking-tight">
                        ResearchOS V3 <span className="text-blue-400 text-xs uppercase ml-2 bg-blue-900/30 px-2 py-1 rounded">Truth Engine</span>
                    </h1>

                    {/* Upload Button */}
                    <label className={`cursor-pointer bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded flex items-center gap-2 transition-colors ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}>
                        <span>{isUploading ? '⏳ Analyzing...' : '📁 Upload PDF'}</span>
                        <input
                            type="file"
                            accept=".pdf"
                            onChange={handleFileUpload}
                            className="hidden"
                            disabled={isUploading}
                        />
                    </label>

                    {uploadedFile && <span className="text-sm text-green-400 font-medium">✅ {uploadedFile}</span>}
                </div>

                <div className="text-xs text-gray-400 bg-gray-700/50 px-3 py-1.5 rounded border border-gray-600">
                    21 CFR Part 11 Mode: <span className="text-green-400 font-bold">ACTIVE</span>
                </div>
            </header>

            {/* Main Content - Takes remaining space, hides overflow */}
            <main className="flex flex-1 overflow-hidden relative">

                {/* PDF Viewer Area - This needs to scroll */}
                <div className="flex-1 flex flex-col min-w-0 bg-gray-100 relative">
                    {pdfUrl ? (
                        // PDFViewer component has its own internal scroll container (Worker -> Viewer)
                        // But we need to ensure this container allows it to expand
                        <div className="flex-1 overflow-hidden relative flex flex-col">
                            <PDFViewer
                                ref={pdfViewerRef}
                                pdfUrl={pdfUrl}
                            />
                        </div>
                    ) : (
                        <div className="flex-1 flex items-center justify-center text-gray-400 overflow-auto">
                            <div className="text-center">
                                <span className="text-4xl block mb-4">📄</span>
                                <p className="text-lg font-medium">No PDF Loaded</p>
                                <p className="text-sm mt-2">Click "📁 Upload PDF" to get started</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Sidebar - Fixed width, independent scroll */}
                <div className="w-96 bg-gray-800 border-l border-gray-700 shadow-2xl flex flex-col z-10 shrink-0">
                    {error && (
                        <div className="p-6 text-red-400 bg-red-900/20 border-b border-red-900/50 shrink-0">
                            <h2 className="font-bold text-lg mb-2 flex items-center gap-2">
                                <span>❌</span> Analysis Failed
                            </h2>
                            <p className="text-sm">{error}</p>
                            <p className="text-xs mt-4 opacity-70">Check if backend is running on port 8000.</p>
                        </div>
                    )}
                    {!error && (
                        <DataSidebar
                            data={data?.verified_data}
                            sessionId={data?.session_id}
                            onSelectField={(location) => {
                                // Direct imperative scroll to ensure we go to the right place
                                if (pdfViewerRef.current) {
                                    pdfViewerRef.current.scrollToAndHighlight(location);
                                }
                            }}
                        />
                    )}
                </div>
            </main>
        </div>
    );
}

export default App;
