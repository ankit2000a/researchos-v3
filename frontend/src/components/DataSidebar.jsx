import React, { useState } from 'react';
import { ShieldAlert, CheckCircle, XCircle, AlertTriangle, MapPin, ChevronDown, ChevronUp } from 'lucide-react';

const DataSidebar = ({ data, onSelectField }) => {
    const [expandedThinking, setExpandedThinking] = useState({});

    if (!data) {
        return (
            <div className="w-96 h-full bg-white border-l border-gray-200 flex items-center justify-center">
                <div className="p-4 text-gray-500 text-center">
                    <ShieldAlert className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>Upload a PDF to see verification results</p>
                </div>
            </div>
        );
    }

    // Handle both 'report' (old format) and 'verified_data' (new format)
    const dataItems = data.verified_data || data.report || {};

    const toggleThinking = (key) => {
        setExpandedThinking(prev => ({ ...prev, [key]: !prev[key] }));
    };

    return (
        <div className="w-96 h-full bg-white border-l border-gray-200 overflow-y-auto flex flex-col">
            <div className="p-4 border-b border-gray-100 bg-gray-50 sticky top-0 z-10">
                <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                    <ShieldAlert className="w-5 h-5 text-blue-600" />
                    Audit Trail
                </h2>
                <p className="text-xs text-gray-500 mt-1">Session ID: {data.session_id?.slice(0, 8)}</p>
            </div>

            <div className="flex-1 p-2">
                {Object.entries(dataItems).map(([key, item]) => {
                    let statusColor = "bg-gray-100 border-gray-200";
                    let Icon = AlertTriangle;
                    let iconColor = "text-gray-600";

                    // Color coding based on verification status
                    if (item.verification_status === "VERIFIED") {
                        statusColor = "bg-green-50 border-green-200";
                        Icon = CheckCircle;
                        iconColor = "text-green-600";
                    } else if (item.verification_status === "CRITICAL_CONFLICT") {
                        statusColor = "bg-red-50 border-red-200";
                        Icon = XCircle;
                        iconColor = "text-red-600";
                    } else if (item.verification_status === "GEOMETRIC_FAIL") {
                        statusColor = "bg-yellow-50 border-yellow-200";
                        Icon = AlertTriangle;
                        iconColor = "text-yellow-600";
                    } else if (item.verification_status === "REVIEW_NEEDED") {
                        statusColor = "bg-orange-50 border-orange-200";
                        Icon = AlertTriangle;
                        iconColor = "text-orange-600";
                    }

                    // Check if coordinates are valid (not null/undefined and has all required properties)
                    const hasValidCoordinates = item.coordinates && 
                        item.coordinates.x !== null && 
                        item.coordinates.y !== null && 
                        item.coordinates.w !== null && 
                        item.coordinates.h !== null &&
                        !(item.coordinates.x === 0 && item.coordinates.y === 0 && 
                          item.coordinates.w === 0 && item.coordinates.h === 0);

                    const isThinkingExpanded = expandedThinking[key];

                    return (
                        <div
                            key={key}
                            onClick={() => hasValidCoordinates && onSelectField(item.coordinates)}
                            className={`mb-3 p-3 rounded-lg border ${statusColor} ${hasValidCoordinates ? 'cursor-pointer hover:shadow-md' : ''} transition-all`}
                        >
                            <div className="flex justify-between items-start mb-2">
                                <span className="font-medium text-sm text-gray-700 capitalize">
                                    {key.replace(/_/g, " ")}
                                </span>
                                <Icon className={`w-4 h-4 ${iconColor}`} />
                            </div>

                            <div className="text-lg font-bold text-gray-900 mb-2">
                                {String(item.extracted_value || item.value)}
                            </div>

                            {/* Location badge */}
                            <div className="mb-2">
                                {hasValidCoordinates ? (
                                    <span className="inline-flex items-center gap-1 text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                                        <MapPin className="w-3 h-3" />
                                        Click to locate
                                    </span>
                                ) : (
                                    <span className="inline-flex items-center gap-1 text-xs bg-gray-200 text-gray-600 px-2 py-1 rounded">
                                        <AlertTriangle className="w-3 h-3" />
                                        NO LOCATION
                                    </span>
                                )}
                            </div>

                            {/* Auditor reasoning */}
                            {item.auditor_reasoning && (
                                <div className="text-xs text-gray-600 bg-white/70 p-2 rounded mb-2">
                                    <strong>Reasoning:</strong> {item.auditor_reasoning}
                                </div>
                            )}

                            {/* Thinking log - expandable */}
                            {item.thinking_log && (
                                <div className="mt-2 border-t border-dashed border-gray-300 pt-2">
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            toggleThinking(key);
                                        }}
                                        className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-700 font-mono w-full"
                                    >
                                        {isThinkingExpanded ? (
                                            <ChevronUp className="w-3 h-3" />
                                        ) : (
                                            <ChevronDown className="w-3 h-3" />
                                        )}
                                        <span>Thinking Log</span>
                                    </button>
                                    {isThinkingExpanded && (
                                        <div className="mt-1 text-[10px] text-gray-400 font-mono whitespace-pre-wrap bg-gray-50 p-2 rounded">
                                            {item.thinking_log}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default DataSidebar;
