import React from 'react';
import { ShieldAlert, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

const DataSidebar = ({ data, onSelectField }) => {
    if (!data) return <div className="p-4">Loading verification results...</div>;

    return (
        <div className="w-96 h-full bg-white border-l border-gray-200 overflow-y-auto flex flex-col">
            <div className="p-4 border-b border-gray-100 bg-gray-50">
                <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                    <ShieldAlert className="w-5 h-5 text-blue-600" />
                    Audit Trail
                </h2>
                <p className="text-xs text-gray-500 mt-1">Session ID: {data.session_id?.slice(0, 8)}</p>
            </div>

            <div className="flex-1 p-2">
                {Object.entries(data.report || {}).map(([key, item]) => {
                    let statusColor = "bg-gray-100";
                    let Icon = AlertTriangle;

                    if (item.verification_status === "VERIFIED") {
                        statusColor = "bg-green-50 border-green-200";
                        Icon = CheckCircle;
                    } else if (item.verification_status === "CRITICAL_CONFLICT") {
                        statusColor = "bg-red-50 border-red-200";
                        Icon = XCircle;
                    } else if (item.verification_status === "GEOMETRIC_FAIL") {
                        statusColor = "bg-yellow-50 border-yellow-200";
                        Icon = AlertTriangle;
                    }

                    return (
                        <div
                            key={key}
                            onClick={() => item.coordinates && onSelectField(item.coordinates)}
                            className={`mb-3 p-3 rounded-lg border ${statusColor} cursor-pointer hover:shadow-md transition-all`}
                        >
                            <div className="flex justify-between items-start mb-1">
                                <span className="font-medium text-sm text-gray-700 capitalize">{key.replace(/_/g, " ")}</span>
                                <Icon className={`w-4 h-4 ${item.verification_status === "VERIFIED" ? "text-green-600" :
                                        item.verification_status === "CRITICAL_CONFLICT" ? "text-red-600" : "text-yellow-600"
                                    }`} />
                            </div>

                            <div className="text-lg font-bold text-gray-900 mb-2">
                                {String(item.extracted_value)}
                            </div>

                            <div className="text-xs text-gray-600 bg-white/50 p-2 rounded">
                                <strong>Reasoning:</strong> {item.auditor_reasoning}
                            </div>

                            {item.thinking_log && (
                                <div className="mt-2 text-[10px] text-gray-400 font-mono border-t border-dashed border-gray-300 pt-1">
                                    Thinking: {item.thinking_log.slice(0, 100)}...
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
