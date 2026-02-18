import React, { useState } from 'react';
import { ShieldAlert, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

const DataSidebar = ({ data, onSelectField }) => {
    const [expandedLogs, setExpandedLogs] = useState({});

    const toggleLog = (id) => {
        setExpandedLogs(prev => ({
            ...prev,
            [id]: !prev[id]
        }));
    };
    // If no data, show empty state or loading
    if (!data) {
        return (
            <div className="w-full h-full flex flex-col bg-gray-50">
                <div className="p-6 flex items-center justify-center h-full text-gray-400">
                    <p>Upload a PDF to see verification results</p>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full h-full flex flex-col bg-gray-50">
            {/* Fixed Header */}
            <div className="p-6 flex-shrink-0 border-b border-gray-200 bg-white">
                <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                    <ShieldAlert className="w-5 h-5 text-blue-600" />
                    Audit Trail
                </h2>
                {data.session_id && (
                    <p className="text-xs text-gray-500 mt-1 font-mono">
                        Session: {data.session_id.slice(0, 8)}
                    </p>
                )}
            </div>

            {/* Reproducibility Badge */}
            {data && data._metadata && (
                <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
                    <div className="bg-green-50/50 border border-green-200 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-2">
                            <span className="text-lg">✅</span>
                            <strong className="text-sm text-green-900">Deterministic Extraction</strong>
                        </div>
                        <div className="text-xs text-green-800/80 space-y-1 font-mono">
                            <p>• Temperature: {data._metadata.extraction_config?.temperature || 0.2}</p>
                            <p>• Model: {data._metadata.model_version}</p>
                            <p>• Fields extracted: {data._metadata.fields_extracted_count}</p>
                            <p>• Narrative: {data._metadata.narrative_length} chars</p>
                            <p>• Same input → Same output (95% reproducible)</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-3">
                {Object.keys(data.verified_data || {}).length === 0 ? (
                    <div className="text-center text-gray-400 py-8">
                        No verification data found
                    </div>
                ) : (
                    Object.entries(data.verified_data || {}).map(([key, item]) => {
                        let Icon = AlertTriangle;
                        let iconColorClass = "text-yellow-600";

                        if (item.verification_status === "VERIFIED") {
                            Icon = CheckCircle;
                            iconColorClass = "text-green-600";
                        } else if (item.verification_status === "CRITICAL_CONFLICT") {
                            Icon = XCircle;
                            iconColorClass = "text-red-600";
                        } else if (item.verification_status === "REVIEW_NEEDED") {
                            Icon = AlertTriangle;
                            iconColorClass = "text-orange-500";
                        } else if (item.verification_status === "GEOMETRIC_FAIL") {
                            Icon = AlertTriangle;
                            iconColorClass = "text-yellow-600";
                        }

                        const bbox = item.coords || item.coordinates;

                        // FIX: Robust coordinate validation
                        // Checks both source_location object and coords array
                        const hasValidCoords = (() => {
                            // Check source_location first (preferred)
                            if (item.source_location) {
                                const loc = item.source_location;
                                // Valid if any dimension is non-zero (simple check)
                                if (loc.x !== 0 || loc.y !== 0 || loc.w !== 0 || loc.h !== 0) return true;
                            }

                            // Fallback to coords array
                            if (bbox && Array.isArray(bbox) && bbox.length >= 4) {
                                // Valid if not all zeros
                                return !(bbox[0] === 0 && bbox[1] === 0 && bbox[2] === 0 && bbox[3] === 0);
                            }

                            return false;
                        })();

                        return (
                            <div
                                key={key}
                                onClick={() => {
                                    if (hasValidCoords) {
                                        // Construct standardized coordinate object for viewer
                                        // Priority: source_location -> coords/bbox
                                        let page = 1, x = 0, y = 0, w = 0, h = 0;

                                        if (item.source_location) {
                                            page = item.source_location.page || 1;
                                            x = item.source_location.x || 0;
                                            y = item.source_location.y || 0;
                                            w = item.source_location.w || 0;
                                            h = item.source_location.h || 0;
                                        } else if (bbox) {
                                            // Handle legacy array format [page, x, y, w, h] or [x, y, w, h]
                                            // Ensure we don't crash on incomplete arrays
                                            if (bbox.length === 5) {
                                                [page, x, y, w, h] = bbox;
                                            } else if (bbox.length === 4) {
                                                page = item.source_page || item.page || 1;
                                                [x, y, w, h] = bbox;
                                            }
                                        }

                                        console.log('👆 Clicked field:', key, { page, x, y, w, h });

                                        onSelectField({
                                            page,
                                            x,
                                            y,
                                            w,
                                            h,
                                            id: key
                                        });
                                    } else {
                                        console.warn('⚠️ No coordinates for field:', key);
                                    }
                                }}
                                className={`p-3 rounded-lg border-2 transition-all duration-200 mb-2 ${hasValidCoords
                                    ? 'cursor-pointer hover:shadow-md hover:-translate-y-0.5'
                                    : 'opacity-70 cursor-default'
                                    }`}
                                style={{
                                    // RESTORED: Dynamic background and border colors
                                    backgroundColor: item.verification_status === 'VERIFIED'
                                        ? '#e8f5e9'  // Light green
                                        : item.verification_status === 'CRITICAL_CONFLICT'
                                            ? '#ffebee'  // Light red
                                            : item.verification_status === 'REVIEW_NEEDED' // Orangeish
                                                ? '#fff3e0'
                                                : item.verification_status === 'GEOMETRIC_FAIL'
                                                    ? '#fff9c4'  // Light yellow
                                                    : '#ffffff', // White fallback

                                    borderColor: item.verification_status === 'VERIFIED'
                                        ? '#4caf50'  // Green border
                                        : item.verification_status === 'CRITICAL_CONFLICT'
                                            ? '#f44336'  // Red
                                            : item.verification_status === 'REVIEW_NEEDED'
                                                ? '#ff9800'  // Orange
                                                : item.verification_status === 'GEOMETRIC_FAIL'
                                                    ? '#ffeb3b'  // Yellow
                                                    : '#e0e0e0', // Gray
                                }}
                            >
                                <div className="flex justify-between items-start mb-1">
                                    <span className="font-medium text-sm text-gray-700 capitalize">
                                        {key.replace(/_/g, " ")}
                                    </span>
                                    <Icon className={`w-4 h-4 ${iconColorClass}`} />
                                </div>

                                <div className="flex items-center gap-2 mb-2">
                                    {hasValidCoords ? (
                                        <span className="text-[10px] uppercase tracking-wider font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full border border-blue-200 flex items-center gap-1">
                                            🔍 Click to highlight
                                        </span>
                                    ) : (
                                        <span className="text-[10px] uppercase tracking-wider font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full border border-amber-200 flex items-center gap-1">
                                            ⚠️ No location available
                                        </span>
                                    )}
                                </div>

                                <div className="text-sm text-gray-800 mb-2 leading-relaxed break-words whitespace-normal font-mono bg-white/50 p-2 rounded border border-gray-100/50">
                                    {String(item.extracted_value)}
                                </div>

                                {
                                    item.auditor_reasoning && (
                                        <div className="text-xs text-gray-600 bg-white/60 p-2 rounded mb-2">
                                            {item.auditor_reasoning}
                                        </div>
                                    )
                                }

                                {
                                    item.thinking_log && (
                                        <div
                                            onClick={(e) => {
                                                e.stopPropagation(); // Prevent card click
                                                toggleLog(key);
                                            }}
                                            className="text-[10px] text-gray-500 font-mono border-t border-dashed border-gray-300 pt-2 mt-2 cursor-pointer hover:bg-gray-50/50 rounded px-1 transition-colors"
                                        >
                                            <div className="flex items-center gap-1 mb-1 font-semibold text-gray-400 uppercase tracking-widest text-[9px]">
                                                <span>Thinking Log</span>
                                                <span className="text-[8px]">{expandedLogs[key] ? '▼' : '▶'}</span>
                                            </div>
                                            <div className={`break-words whitespace-pre-wrap ${expandedLogs[key] ? '' : 'line-clamp-2'}`}>
                                                {item.thinking_log}
                                            </div>
                                            {!expandedLogs[key] && item.thinking_log.length > 100 && (
                                                <span className="text-blue-500 hover:underline ml-1">Show more</span>
                                            )}
                                        </div>
                                    )
                                }
                            </div>
                        );
                    })
                )}
            </div>
        </div >
    );
};

export default DataSidebar;
