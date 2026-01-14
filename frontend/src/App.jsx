import React, { useState, useEffect } from 'react';
import PDFViewer from './components/PDFViewer';
import DataSidebar from './components/DataSidebar';
import { AlertTriangle } from 'lucide-react';

// Using absolute path for PDF to avoid import issues
const PDF_URL = "/conflict_study.pdf";

function App() {
    const [activeBox, setActiveBox] = useState(null);
    const [data, setData] = useState(null);

    // Poll backend for results (Simulated interaction)
    useEffect(() => {
        // In a real app, we'd trigger the audit via POST /api/audit first.
        // Here we assume the backend is running and we fetch the 'latest' result.
        const fetchData = async () => {
            try {
                // Trigger audit (idempotent for mock)
                await fetch("http://localhost:8000/api/audit", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ file_path: "conflict_study.pdf" })
                });

                // Get results
                const res = await fetch("http://localhost:8000/api/results");
                const json = await res.json();
                setData(json);
            } catch (e) {
                console.error("API Error:", e);
            }
        };

        fetchData();
    }, []);

    return (
        <div className="flex h-screen w-screen bg-gray-900 text-white font-sans overflow-hidden">
            {/* Main Content Area */}
            <div className="flex-1 flex flex-col relative">
                <header className="h-14 bg-gray-800 border-b border-gray-700 flex items-center px-4 justify-between z-20">
                    <h1 className="font-bold text-lg tracking-tight">ResearchOS V3 <span className="text-blue-400 text-xs uppercase ml-2 bg-blue-900/30 px-2 py-1 rounded">Truth Engine</span></h1>
                    <div className="text-xs text-gray-400">21 CFR Part 11 Mode: ACTIVE</div>
                </header>

                <div className="flex-1 relative z-10">
                    <PDFViewer
                        pdfUrl={PDF_URL}
                        activeBox={activeBox}
                    />
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
