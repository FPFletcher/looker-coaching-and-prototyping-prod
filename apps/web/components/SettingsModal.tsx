import { useState, useEffect } from 'react';
import { X, Settings as SettingsIcon, Database, Key, RotateCcw, ChevronDown } from 'lucide-react';

// Default credentials (masked in UI — type "default" to revert)
const DEFAULT_CREDENTIALS = {
    url: 'https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app',
    client_id: 'CXy7CKWwYMjjQrHzzgxZ',
    client_secret: 'J6KYGFmpNPwwfmFrHWXB3KGG',
    vertex_api_key: 'AQ.Ab8RN6Ljoi9PCQfD3fEgEQ-wiAogIYtnLag_fMpIYVJo9XmboQ',
    claude_api_key: '',
    google_api_key: '',
};

export interface LookerCredentials {
    url: string;
    client_id: string;
    client_secret: string;
}

export interface SettingsData {
    credentials: LookerCredentials;
    mode: 'existing' | 'dummy';
    model: string;
    useVertex: boolean;
    gcpProject?: string;
    gcpLocation?: string;
    vertexApiKey?: string;
    claudeApiKey?: string;
    googleApiKey?: string;
}

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (settings: SettingsData) => void;
    initialSettings?: SettingsData;
}

export default function SettingsModal({ isOpen, onClose, onSave, initialSettings }: SettingsModalProps) {
    const [url, setUrl] = useState(initialSettings?.credentials.url || '');
    const [clientId, setClientId] = useState(initialSettings?.credentials.client_id || '');
    const [clientSecret, setClientSecret] = useState(initialSettings?.credentials.client_secret || '');
    const [mode, setMode] = useState<'existing' | 'dummy'>(initialSettings?.mode || 'existing');
    const [model, setModel] = useState(initialSettings?.model || 'claude-sonnet-4-6');
    const [gcpProject, setGcpProject] = useState(initialSettings?.gcpProject || 'looker-core-demo-ffrancois');
    const [gcpLocation, setGcpLocation] = useState(initialSettings?.gcpLocation || 'europe-west1');

    // AI Credentials
    const [useVertex, setUseVertex] = useState(initialSettings?.useVertex ?? true);
    const [vertexApiKey, setVertexApiKey] = useState(initialSettings?.vertexApiKey || DEFAULT_CREDENTIALS.vertex_api_key);
    const [claudeApiKey, setClaudeApiKey] = useState(initialSettings?.claudeApiKey || DEFAULT_CREDENTIALS.claude_api_key);
    const [googleApiKey, setGoogleApiKey] = useState(initialSettings?.googleApiKey || DEFAULT_CREDENTIALS.google_api_key);

    const [showSecret, setShowSecret] = useState(false);
    const [showClientId, setShowClientId] = useState(false); // Added toggle for Client ID
    const [showVertexKey, setShowVertexKey] = useState(false);
    const [showClaudeKey, setShowClaudeKey] = useState(false);
    const [showGoogleKey, setShowGoogleKey] = useState(false);
    const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);

    const isDefaultCred = (val: string, field: keyof typeof DEFAULT_CREDENTIALS) => val === DEFAULT_CREDENTIALS[field] || (field === 'vertex_api_key' && val === 'AQ.Ab8RN6IApYrJpLv1jipHJww-hpKCffNayNpfpe7tP66DJjT15w');

    const handleClientIdChange = (val: string) => {
        if (val.toLowerCase() === 'default') { setClientId(DEFAULT_CREDENTIALS.client_id); }
        else setClientId(val);
    };
    const handleVertexKeyChange = (val: string) => {
        if (val.toLowerCase() === 'default') { setVertexApiKey(DEFAULT_CREDENTIALS.vertex_api_key); }
        else setVertexApiKey(val);
    };
    const handleClaudeKeyChange = (val: string) => {
        if (val.toLowerCase() === 'default') { setClaudeApiKey(DEFAULT_CREDENTIALS.claude_api_key); }
        else setClaudeApiKey(val);
    };
    const handleGoogleKeyChange = (val: string) => {
        if (val.toLowerCase() === 'default') { setGoogleApiKey(DEFAULT_CREDENTIALS.google_api_key); }
        else setGoogleApiKey(val);
    };
    const handleClientSecretChange = (val: string) => {
        if (val.toLowerCase() === 'default') { setClientSecret(DEFAULT_CREDENTIALS.client_secret); }
        else setClientSecret(val);
    };
    const handleUrlChange = (val: string) => {
        if (val.toLowerCase() === 'default') { setUrl(DEFAULT_CREDENTIALS.url); }
        else setUrl(val);
    };
    const handleRevertAll = () => {
        setUrl(DEFAULT_CREDENTIALS.url);
        setClientId(DEFAULT_CREDENTIALS.client_id);
        setClientSecret(DEFAULT_CREDENTIALS.client_secret);
        setVertexApiKey(DEFAULT_CREDENTIALS.vertex_api_key);
        setClaudeApiKey(DEFAULT_CREDENTIALS.claude_api_key);
    };

    useEffect(() => {
        if (initialSettings) {
            setUrl(initialSettings.credentials.url);
            setClientId(initialSettings.credentials.client_id);
            setClientSecret(initialSettings.credentials.client_secret);
            setMode(initialSettings.mode);
            setModel(initialSettings.model);
            setGcpProject(initialSettings.gcpProject || 'looker-core-demo-ffrancois');
            setGcpLocation(initialSettings.gcpLocation || 'europe-west1');
            setUseVertex(initialSettings.useVertex ?? true);
            setVertexApiKey(initialSettings.vertexApiKey || DEFAULT_CREDENTIALS.vertex_api_key);
            setClaudeApiKey(initialSettings.claudeApiKey || DEFAULT_CREDENTIALS.claude_api_key);
            setGoogleApiKey(initialSettings.googleApiKey || DEFAULT_CREDENTIALS.google_api_key);
        }
    }, [initialSettings]);

    const handleSave = () => {
        // Basic validation
        if (!url || !clientId || !clientSecret) {
            alert('Please fill in all fields');
            return;
        }

        const settings: SettingsData = {
            credentials: { url, client_id: clientId, client_secret: clientSecret },
            mode,
            model,
            useVertex,
            gcpProject,
            gcpLocation,
            vertexApiKey,
            claudeApiKey,
            googleApiKey,
        };

        onSave(settings);
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="bg-[#1e1f20] border border-[#37393b] rounded-lg w-full max-w-md p-6 shadow-2xl overflow-y-auto max-h-[90vh]">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-500/10 rounded-lg">
                            <SettingsIcon className="w-5 h-5 text-blue-400" />
                        </div>
                        <h2 className="text-xl font-semibold text-white">Looker Settings</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 hover:bg-[#37393b] rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-400" />
                    </button>
                </div>

                {/* Mode Selection */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-300 mb-3">Mode</label>
                    <div className="flex gap-3">
                        <button
                            onClick={() => setMode('existing')}
                            className={`flex-1 p-3 rounded-lg border transition-all ${mode === 'existing'
                                ? 'bg-blue-500/10 border-blue-500/50 text-blue-400'
                                : 'bg-[#2a2b2c] border-[#37393b] text-gray-400 hover:border-gray-600'
                                }`}
                        >
                            <Database className="w-5 h-5 mx-auto mb-1" />
                            <div className="text-sm font-medium">Use Existing Data</div>
                        </button>
                        <button
                            onClick={() => setMode('dummy')}
                            disabled
                            className="flex-1 p-3 rounded-lg border bg-[#2a2b2c]/50 border-[#37393b] text-gray-600 cursor-not-allowed opacity-50"
                        >
                            <Key className="w-5 h-5 mx-auto mb-1" />
                            <div className="text-sm font-medium">Create Dummy Data</div>
                            <div className="text-xs mt-1">(Coming Soon)</div>
                        </button>
                    </div>
                </div>

                {/* Model Selection */}
                <div className="mb-6">
                    <label htmlFor="model-select" className="block text-sm font-medium text-gray-300 mb-2">
                        AI Model
                    </label>
                    <select
                        id="model-select"
                        value={model}
                        onChange={(e) => setModel(e.target.value)}
                        className="w-full px-3 py-2 bg-[#2a2b2c] border border-[#37393b] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
                    >
                        <optgroup label="Claude Models">
                            <option value="claude-sonnet-4-6">Claude Sonnet 4.6 (Recommended)</option>
                            <option value="claude-opus-4-6">Claude Opus 4.6</option>
                            <option value="claude-sonnet-4-5">Claude Sonnet 4.5</option>
                        </optgroup>
                        <optgroup label="Gemini Models">
                            <option value="gemini-3.1-pro-preview">Gemini 3.1 Pro (Preview)</option>
                            <option value="gemini-3.1-flash-lite-preview">Gemini 3.1 Flash Lite (Preview)</option>
                            <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                            <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                            <option value="gemini-2.5-flash-lite">Gemini 2.5 Flash-Lite</option>
                        </optgroup>
                    </select>
                </div>

                {/* Credentials Form */}
                <div className="space-y-4 mb-6 pt-4 border-t border-[#37393b]">
                    <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-400">Looker Credentials</span>
                        <button
                            type="button"
                            onClick={handleRevertAll}
                            title="Reset to default credentials"
                            className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                        >
                            <RotateCcw className="w-3 h-3" /> Revert to default
                        </button>
                    </div>
                    <div>
                        <label htmlFor="looker-url" className="block text-sm font-medium text-gray-300 mb-2">
                            Looker Instance URL
                        </label>
                        <input
                            id="looker-url"
                            type="url"
                            value={url}
                            onChange={(e) => handleUrlChange(e.target.value)}
                            placeholder="https://your-instance.looker.app (type 'default' to revert)"
                            className={`w-full px-3 py-2 bg-[#2a2b2c] border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 ${isDefaultCred(url, 'url') ? 'border-green-500/40' : 'border-[#37393b]'
                                }`}
                        />
                        {isDefaultCred(url, 'url') && <p className="text-xs text-green-400 mt-1">✓ Using default instance</p>}
                    </div>

                    <div>
                        <label htmlFor="client-id" className="block text-sm font-medium text-gray-300 mb-2">
                            Client ID <span className="text-gray-500 text-xs font-normal">(type "default" to revert)</span>
                        </label>
                        <div className="relative">
                            <input
                                id="client-id"
                                type={showClientId ? 'text' : 'password'}
                                value={isDefaultCred(clientId, 'client_id') ? (showClientId ? 'default' : '••••••••••••••••••••') : clientId}
                                onFocus={(e) => { if (isDefaultCred(clientId, 'client_id') && !showClientId) { e.target.value = ''; setShowClientId(true); } else if (e.target.value === 'default') { e.target.value = ''; } }}
                                onChange={(e) => handleClientIdChange(e.target.value)}
                                placeholder="Enter client ID (type 'default' to revert)"
                                className={`w-full px-3 py-2 bg-[#2a2b2c] border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 pr-20 ${isDefaultCred(clientId, 'client_id') ? 'border-green-500/40' : 'border-[#37393b]'
                                    }`}
                            />
                            <button
                                type="button"
                                onClick={() => setShowClientId(!showClientId)}
                                className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-xs text-gray-400 hover:text-white transition-colors"
                            >
                                {showClientId ? 'Hide' : 'Show'}
                            </button>
                        </div>
                        {isDefaultCred(clientId, 'client_id') && <p className="text-xs text-green-400 mt-1">✓ Using default credentials</p>}
                    </div>

                    <div>
                        <label htmlFor="client-secret" className="block text-sm font-medium text-gray-300 mb-2">
                            Client Secret <span className="text-gray-500 text-xs font-normal">(type "default" to revert)</span>
                        </label>
                        <div className="relative">
                            <input
                                id="client-secret"
                                type={showSecret ? 'text' : 'password'}
                                value={isDefaultCred(clientSecret, 'client_secret') ? (showSecret ? 'default' : '••••••••••••••••••••') : clientSecret}
                                onFocus={(e) => { if (isDefaultCred(clientSecret, 'client_secret') && !showSecret) { e.target.value = ''; setShowSecret(true); } else if (e.target.value === 'default') { e.target.value = ''; } }}
                                onChange={(e) => handleClientSecretChange(e.target.value)}
                                autoComplete="new-password"
                                placeholder="Enter client secret (type 'default' to revert)"
                                className={`w-full px-3 py-2 bg-[#2a2b2c] border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 pr-20 ${isDefaultCred(clientSecret, 'client_secret') ? 'border-green-500/40' : 'border-[#37393b]'
                                    }`}
                            />
                            <button
                                type="button"
                                onClick={() => setShowSecret(!showSecret)}
                                className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-xs text-gray-400 hover:text-white transition-colors"
                            >
                                {showSecret ? 'Hide' : 'Show'}
                            </button>
                        </div>
                        {isDefaultCred(clientSecret, 'client_secret') && <p className="text-xs text-green-400 mt-1">✓ Using default credentials</p>}
                    </div>
                </div>

                {/* AI & Cloud Credentials */}
                <div className="mb-6 pt-4 border-t border-[#37393b]">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-sm font-medium text-gray-400">AI & Cloud Credentials</h3>
                    </div>

                    <div className="mb-4">
                        <label htmlFor="vertex-sa-key" className="block text-sm font-medium text-gray-300 mb-2">
                            Vertex AI Service Account JSON Key (Claude Models)
                        </label>
                        <div className="relative">
                            <textarea
                                id="vertex-sa-key"
                                rows={4}
                                value={isDefaultCred(vertexApiKey, 'vertex_api_key') ? (showVertexKey ? 'default' : '••••••••••••••••••••') : vertexApiKey}
                                onFocus={(e) => { if (isDefaultCred(vertexApiKey, 'vertex_api_key') && !showVertexKey) { e.target.value = ''; setShowVertexKey(true); } else if (e.target.value === 'default') { e.target.value = ''; } }}
                                onChange={(e) => handleVertexKeyChange(e.target.value)}
                                placeholder="Paste API Key (AIza...) or entire Service Account JSON content here..."
                                className={`w-full px-3 py-2 bg-[#2a2b2c] border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 pr-20 text-xs font-mono ${isDefaultCred(vertexApiKey, 'vertex_api_key') ? 'border-green-500/40' : 'border-[#37393b]'}`}
                            />
                            <button
                                type="button"
                                onClick={() => setShowVertexKey(!showVertexKey)}
                                className="absolute right-2 top-2 px-2 py-1 text-xs text-gray-400 hover:text-white transition-colors bg-[#2a2b2c] border border-gray-600 rounded"
                            >
                                {showVertexKey ? 'Hide' : 'Show'}
                            </button>
                        </div>
                        {isDefaultCred(vertexApiKey, 'vertex_api_key') && <p className="text-xs text-green-400 mt-1">✓ Using Server Native IAM Identity</p>}
                    </div>

                    <div>
                        <label htmlFor="google-api-key" className="block text-sm font-medium text-gray-300 mb-2">
                            Google AI Studio API Key (Gemini Models)
                        </label>
                        <div className="relative">
                            <input
                                id="google-api-key"
                                type={showGoogleKey ? 'text' : 'password'}
                                value={isDefaultCred(googleApiKey, 'google_api_key') ? (showGoogleKey ? 'default' : '••••••••••••••••••••') : googleApiKey}
                                onFocus={(e) => { if (isDefaultCred(googleApiKey, 'google_api_key') && !showGoogleKey) { e.target.value = ''; setShowGoogleKey(true); } else if (e.target.value === 'default') { e.target.value = ''; } }}
                                onChange={(e) => handleGoogleKeyChange(e.target.value)}
                                placeholder="Enter Google AI Studio API Key"
                                className={`w-full px-3 py-2 bg-[#2a2b2c] border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 pr-20 ${isDefaultCred(googleApiKey, 'google_api_key') ? 'border-green-500/40' : 'border-[#37393b]'}`}
                            />
                            <button
                                type="button"
                                onClick={() => setShowGoogleKey(!showGoogleKey)}
                                className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-xs text-gray-400 hover:text-white transition-colors"
                            >
                                {showGoogleKey ? 'Hide' : 'Show'}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Info Box */}
                <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                    <p className="text-xs text-blue-300">
                        Your credentials are stored locally in your browser and never sent to external servers.
                    </p>
                </div>

                {/* Actions */}
                <div className="flex gap-3 mt-6">
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2 bg-[#2a2b2c] hover:bg-[#37393b] text-gray-300 rounded-lg transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
                    >
                        Save Settings
                    </button>
                </div>
            </div>
        </div>
    );
}
