import React, { useImperativeHandle, forwardRef, useState, useMemo, useRef, useCallback } from 'react';
import { Worker, Viewer } from '@react-pdf-viewer/core';
import { highlightPlugin } from '@react-pdf-viewer/highlight';
import { pageNavigationPlugin } from '@react-pdf-viewer/page-navigation';
import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/highlight/lib/styles/index.css';

const PDFViewer = forwardRef(({ pdfUrl, onMount }, ref) => {
    const [tempHighlight, setTempHighlight] = useState(null);
    const tempHighlightRef = useRef(tempHighlight);

    // Update ref in effect to avoid mutate-during-render
    React.useEffect(() => {
        tempHighlightRef.current = tempHighlight;
    }, [tempHighlight]);

    const renderHighlights = useCallback((props) => {
        const h = tempHighlightRef.current;
        const show = h && props.pageIndex === h.pageIndex;
        return (
            <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
                {show && (
                    <div
                        style={{
                            background: 'rgba(255, 255, 0, 0.4)',
                            border: '2px solid rgba(255, 0, 0, 0.8)',
                            boxShadow: '0 0 8px rgba(255, 255, 0, 0.5)',
                            position: 'absolute',
                            left: `${h.left}%`,
                            top: `${h.top}%`,
                            width: `${h.width}%`,
                            height: `${h.height}%`,
                            zIndex: 10,
                            pointerEvents: 'none',
                            transition: 'all 0.3s ease-in-out'
                        }}
                    />
                )}
            </div>
        );
    }, []);

    const highlightPluginInstance = highlightPlugin({ renderHighlights });
    const pageNavigationPluginInstance = pageNavigationPlugin();
    
    // We do NOT useMemo plugins array here, because highlightPluginInstance is re-created every render
    // and it acts as a custom hook. Memoizing or useState wrapping it violates Hook rules.
    const plugins = [highlightPluginInstance, pageNavigationPluginInstance];

    const { jumpToPage } = pageNavigationPluginInstance;

    // Allow parent to trigger scroll/highlight via ref. Must be below all hooks.
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

            // Navigate to the correct page
            jumpToPage(pageIndex);

            // Immediate visual feedback (Yellow flash)
            setTempHighlight({
                pageIndex,
                left: x,
                top: y,
                width: w,
                height: h
            });

            // Clear after 4 seconds
            setTimeout(() => {
                setTempHighlight(null);
            }, 4000);
        }
    }));

    // Defensive check MUST be AFTER all hooks (useState, useRef, useCallback, useMemo, useImperativeHandle)
    if (!pdfUrl) return null;

    return (
        <div className="flex-1 overflow-auto bg-gray-100">
            {/* workerUrl points to public static file to avoid Vite hashing issues */}
            <Worker workerUrl="/pdf.worker.min.js">
                <Viewer
                    fileUrl={pdfUrl}
                    plugins={plugins}
                    defaultScale={1.2}
                />
            </Worker>
        </div>
    );
});

export default PDFViewer;
