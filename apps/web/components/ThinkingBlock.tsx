import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Check, X, Loader } from 'lucide-react';

interface ToolExecution {
    name: string;
    input: any;
    output?: any;
    status: 'running' | 'success' | 'error';
    duration?: number;
}

interface ThinkingBlockProps {
    tool: ToolExecution;
}

const ThinkingBlock: React.FC<ThinkingBlockProps> = ({ tool }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    const getStatusColor = () => {
        switch (tool.status) {
            case 'success': return 'text-green-400 bg-green-900/20';
            case 'error': return 'text-red-400 bg-red-900/20';
            case 'running': return 'text-blue-400 bg-blue-900/20';
            default: return 'text-gray-400 bg-gray-900/20';
        }
    };

    const getStatusIcon = () => {
        switch (tool.status) {
            case 'success': return <Check className="w-4 h-4" />;
            case 'error': return <X className="w-4 h-4" />;
            case 'running': return <Loader className="w-4 h-4 animate-spin" />;
            default: return null;
        }
    };

    const getToolIcon = () => {
        const iconMap: { [key: string]: string } = {
            'get_models': '📚',
            'get_explores': '🔍',
            'make_dashboard': '📊',
            'add_dashboard_element': '📈',
            'get_dimensions': '📐',
            'get_measures': '📏',
            'run_query': '▶️',
        };
        return iconMap[tool.name] || '🔧';
    };

    return (
        <div className={`rounded-lg border ${getStatusColor()} mb-2 overflow-hidden`}>
            {/* Header */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full px-4 py-2 flex items-center justify-between hover:bg-white/5 transition-colors"
            >
                <div className="flex items-center gap-2">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    <span className="text-lg">{getToolIcon()}</span>
                    <span className="font-mono text-sm">{tool.name}</span>
                    {tool.input?.fields && Array.isArray(tool.input.fields) && (
                        <span className="text-xs text-gray-400 ml-2 truncate max-w-[200px]">
                            [{tool.input.fields.slice(0, 3).join(', ')}{tool.input.fields.length > 3 ? '...' : ''}]
                        </span>
                    )}
                    {tool.input?.agent_id && (
                        <span className="text-xs text-gray-400 ml-2">
                            ({tool.input.agent_id})
                        </span>
                    )}
                    {tool.duration && (
                        <span className="text-xs text-gray-500">
                            ({tool.duration.toFixed(1)}s)
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    {getStatusIcon()}
                </div>
            </button>

            {/* Expanded Content */}
            {isExpanded && (
                <div className="px-4 py-3 bg-black/20 border-t border-white/10">
                    {/* Input */}
                    {tool.input && Object.keys(tool.input).length > 0 && (
                        <div className="mb-3">
                            <div className="text-xs text-gray-400 mb-1">Input:</div>
                            <pre className="text-xs bg-black/30 p-2 rounded whitespace-pre-wrap break-words">
                                {JSON.stringify(tool.input, null, 2)}
                            </pre>
                        </div>
                    )}

                    {/* Output */}
                    {tool.output && (
                        <div>
                            <div className="text-xs text-gray-400 mb-1">
                                {tool.status === 'error' ? 'Error:' : 'Result:'}
                            </div>
                            <pre className="text-xs bg-black/30 p-2 rounded whitespace-pre-wrap break-words max-h-60 overflow-y-auto">
                                {typeof tool.output === 'string'
                                    ? tool.output
                                    : JSON.stringify(tool.output, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default ThinkingBlock;
