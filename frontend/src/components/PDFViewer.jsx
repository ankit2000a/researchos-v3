import React, { useEffect, useImperativeHandle, forwardRef, useState } from 'react';
import { Worker, Viewer } from '@react-pdf-viewer/core';
import { highlightPlugin } from '@react-pdf-viewer/highlight';
import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/highlight/lib/styles/index.css';

const PDFViewer = forwardRef(({ pdfUrl, activeBox, onMount }, ref) => {
    const [tempHighlight, setTempHighlight] = useState(null);

    // Defensive check
    if (!pdfUrl) return null;

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

    // Allow parent to trigger scroll/highlight via ref
    useImperativeHandle(ref, () => ({
        scrollToAndHighlight: (location) => {
            if (!location) return;

            console.log('🔦 PDFViewer received scroll request:', location);
            const { page, x, y, w, h } = location;

            // Note: API uses 1-based page numbers, Viewer uses 0-based index
            let pageIndex = 0;
            if (typeof page === 'number') {
                pageIndex = page > 0 ? page - 1 : 0;
            }

            // Use the library's built-in jump function
            // It expects: { pageIndex, left, top, width, height }
            jumpToHighlightArea({
                pageIndex: pageIndex,
                left: x,
                top: y,
                width: w,
                height: h
            });

            // Immediate visual feedback (Yellow flash)
            setTempHighlight({
                pageIndex,
                left: x,
                top: y,
                width: w,
                height: h
            });

            // Clear after 3 seconds
            setTimeout(() => {
                setTempHighlight(null);
            }, 3000);
        }
    }));

    // --- SYNC-CLICK LOGIC (Keep for backward compatibility if needed) ---
    useEffect(() => {
        if (activeBox) {
            jumpToHighlightArea({
                pageIndex: activeBox.page > 0 ? activeBox.page - 1 : 0,
                left: activeBox.x,
                top: activeBox.y,
                width: activeBox.w,
                height: activeBox.h
            });
        }
    }, [activeBox]);

    const renderHighlights = (props) => {
        const currentHighlight = tempHighlight || (activeBox ? {
            pageIndex: activeBox.page > 0 ? activeBox.page - 1 : 0,
            left: activeBox.x,
            top: activeBox.y,
            width: activeBox.w,
            height: activeBox.h
        } : null);

        if (!currentHighlight) return <></>;
        if (props.pageIndex !== currentHighlight.pageIndex) return <></>;

        const scale = props.scale;

        return (
            <div>
                <div
                    key="highlight-box"
                    className="highlight-box"
                    style={{
                        background: 'rgba(255, 255, 0, 0.4)', // Visible yellow
                        border: '2px solid rgba(255, 0, 0, 0.8)', // Red border for visibility
                        boxShadow: '0 0 8px rgba(255, 255, 0, 0.5)',
                        position: 'absolute',
                        left: `${currentHighlight.left}%`,
                        top: `${currentHighlight.top}%`,
                        width: `${currentHighlight.width}%`,
                        height: `${currentHighlight.height}%`,
                        zIndex: 10,
                        pointerEvents: 'none', // Allow clicking through
                        transition: 'all 0.3s ease-in-out'
                    }}
                />
            </div>
        );
    };

    return (
        <div className="flex-1 overflow-auto bg-gray-100">
            {/* workerUrl points to public static file to avoid Vite hashing issues */}
            <Worker workerUrl="/pdf.worker.min.js">
                <Viewer
                    fileUrl={pdfUrl}
                    plugins={[highlightPluginInstance]}
                    renderPageLayer={renderHighlights}
                    defaultScale={1.2}
                />
            </Worker>
        </div>
    );
});

export default PDFViewer;
