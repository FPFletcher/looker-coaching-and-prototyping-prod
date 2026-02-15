import React, { useState, useEffect } from 'react';
import { ChevronDown, Database } from 'lucide-react';
import { getApiUrl } from '@/lib/apiConfig';

interface Explore {
    name: string;
    label: string;
    model: string;
}

interface ExploreSelectorProps {
    lookerUrl: string;
    clientId: string;
    clientSecret: string;
    onSelectExplore: (explore: Explore | null) => void;
    selectedExplore: Explore | null;
    disabled?: boolean;
}

const ExploreSelector: React.FC<ExploreSelectorProps> = ({
    lookerUrl,
    clientId,
    clientSecret,
    onSelectExplore,
    selectedExplore,
    disabled = false
}) => {
    const [explores, setExplores] = useState<Explore[]>([]);
    const [loading, setLoading] = useState(false);
    const [isOpen, setIsOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        if (lookerUrl && clientId && clientSecret) {
            fetchExplores();
        }
    }, [lookerUrl, clientId, clientSecret]);

    const fetchExplores = async () => {
        setLoading(true);
        try {
            const response = await fetch(`${getApiUrl()}/api/explores`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    credentials: { url: lookerUrl, client_id: clientId, client_secret: clientSecret }
                })
            });

            if (response.ok) {
                const data = await response.json();
                setExplores(data.explores || []);
            }
        } catch (error) {
            console.error('Failed to fetch explores:', error);
        } finally {
            setLoading(false);
        }
    };

    // Filter explores based on search query
    const filteredExplores = explores.filter(explore => {
        const query = searchQuery.toLowerCase();
        return (
            explore.label.toLowerCase().includes(query) ||
            explore.model.toLowerCase().includes(query) ||
            explore.name.toLowerCase().includes(query)
        );
    });

    const groupedExplores = filteredExplores.reduce((acc, explore) => {
        if (!acc[explore.model]) {
            acc[explore.model] = [];
        }
        acc[explore.model].push(explore);
        return acc;
    }, {} as Record<string, Explore[]>);

    return (
        <div className={`relative w-full max-w-md ${disabled ? 'opacity-50 pointer-events-none' : ''}`}>
            <button
                onClick={() => !disabled && setIsOpen(!isOpen)}
                disabled={disabled}
                className={`w-full flex items-center justify-between px-4 py-2.5 bg-[#2a2b2c] border border-[#37393b] rounded-lg text-white transition-colors ${!disabled && 'hover:bg-[#333537]'}`}
            >
                <div className="flex items-center gap-2">
                    <Database className="w-4 h-4 text-gray-400" />
                    <span className="text-sm">
                        {disabled ? 'POC Mode (Context Only)' : (selectedExplore ? `${selectedExplore.model} › ${selectedExplore.label}` : 'Any Explore (Let AI Choose)')}
                    </span>
                </div>
                {!disabled && <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />}
            </button>

            {isOpen && (
                <div className="absolute top-full mt-2 w-full bg-[#2a2b2c] border border-[#37393b] rounded-lg shadow-lg max-h-96 overflow-y-auto z-50">
                    {/* Search Input */}
                    <div className="sticky top-0 bg-[#2a2b2c] p-3 border-b border-[#37393b]">
                        <input
                            type="text"
                            placeholder="Search explores..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full px-3 py-2 bg-[#1e1f20] border border-[#37393b] rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
                            onClick={(e) => e.stopPropagation()}
                        />
                    </div>

                    <div
                        onClick={() => {
                            onSelectExplore(null);
                            setIsOpen(false);
                            setSearchQuery('');
                        }}
                        className="px-4 py-2 hover:bg-[#333537] cursor-pointer transition-colors"
                    >
                        <div className="text-sm font-medium text-white">Any Model</div>
                        <div className="text-xs text-gray-400">Let AI choose the best model automatically</div>
                    </div>

                    <div className="border-t border-[#37393b]"></div>

                    {loading ? (
                        <div className="px-4 py-3 text-sm text-gray-400">Loading explores...</div>
                    ) : Object.keys(groupedExplores).length === 0 ? (
                        <div className="px-4 py-3 text-sm text-gray-400">
                            {searchQuery ? 'No explores match your search' : 'No explores available'}
                        </div>
                    ) : (
                        Object.entries(groupedExplores).map(([model, modelExplores]) => (
                            <div key={model} className="border-t border-[#37393b]">
                                <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase">{model}</div>
                                {modelExplores.map((explore) => (
                                    <div
                                        key={`${explore.model}-${explore.name}`}
                                        onClick={() => {
                                            onSelectExplore(explore);
                                            setIsOpen(false);
                                            setSearchQuery('');
                                        }}
                                        className="px-4 py-2 hover:bg-[#333537] cursor-pointer transition-colors flex items-center justify-between"
                                    >
                                        <span className="text-sm text-white">{explore.label}</span>
                                        {selectedExplore?.name === explore.name && selectedExplore?.model === explore.model && (
                                            <span className="text-xs text-blue-400">✓</span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
};

export default ExploreSelector;
