import React, { useEffect } from 'react';
import { Worker, Viewer } from '@react-pdf-viewer/core';
import { highlightPlugin } from '@react-pdf-viewer/highlight';
import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/highlight/lib/styles/index.css';

const PDFViewer = ({ pdfUrl, activeBox, onMount }) => {
    const highlightPluginInstance = highlightPlugin({
        renderHighlightTarget: (props) => (
            <div
                style={{
                    background: '#eee',
                    display: 'flex',
                    position: 'absolute',
                    left: `${props.selectionRegion.left}%`,
                    top: `${props.selectionRegion.top + props.selectionRegion.height}%`,
                    zIndex: 1,
                }}
            />
        ),
    });

    const { jumpToHighlightArea } = highlightPluginInstance;

    // --- SYNC-CLICK LOGIC ---
    useEffect(() => {
        if (activeBox) {
            jumpToHighlightArea({
                pageIndex: activeBox.page - 1, // API is 1-based, Viewer is 0-based
                left: activeBox.x,
                top: activeBox.y,
                width: activeBox.w,
                height: activeBox.h
            });
        }
    }, [activeBox]);

    const renderHighlights = (props) => {
        if (!activeBox) return <></>;
        if (props.pageIndex !== activeBox.page - 1) return <></>;

        const scale = props.scale; // --- SCALING FIX ---

        return (
            <div>
                <div
                    key={activeBox.id}
                    className="highlight-box"
                    style={{
                        background: 'rgba(255, 0, 0, 0.2)',
                        border: '2px solid red',
                        position: 'absolute',
                        // Multiply by scale to prevent Drift
                        left: `${activeBox.x * scale}px`,
                        top: `${activeBox.y * scale}px`,
                        width: `${activeBox.w * scale}px`,
                        height: `${activeBox.h * scale}px`,
                        zIndex: 10,
                    }}
                />
            </div>
        );
    };

    return (
        <div className="h-full w-full overflow-hidden bg-gray-100">
            {/* workerUrl points to public static file to avoid Vite hashing issues */}
            <Worker workerUrl="/pdf.worker.min.js">
                <Viewer
                    fileUrl={pdfUrl}
                    plugins={[highlightPluginInstance]}
                    renderPageLayer={renderHighlights}
                />
            </Worker>
        </div>
    );
};

export default PDFViewer;
