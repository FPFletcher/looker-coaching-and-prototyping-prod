import React, { useEffect, useState } from 'react';

interface DashboardEmbedProps {
    url: string;
}

const DashboardEmbed: React.FC<DashboardEmbedProps> = ({ url }) => {
    const [embedError, setEmbedError] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    // Extract valid ID or Slug for Dashboard or Explore
    const extractResourceId = (resource_url: string): { type: 'dashboard' | 'explore', id: string } | null => {
        // Check for Explore with qid
        if (resource_url.includes('/explore/')) {
            const match = resource_url.match(/\/explore\/([^\?]+)/);
            if (match) return { type: 'explore', id: match[1] }; // We'll actually use the full path for explore
        }

        // Check for Dashboard
        const match = resource_url.match(/(?:dashboards\/|embed\/dashboards\/)([a-zA-Z0-9\-_]+)/);
        if (match) return { type: 'dashboard', id: match[1] };

        return null;
    };

    const resource = extractResourceId(url) || { type: 'dashboard', id: 'unknown' };

    // Reset error state when URL changes
    useEffect(() => {
        setEmbedError(false);
        setIsLoading(true);
    }, [url]);

    // DEBUG: Log when this component mounts/unmounts/re-renders
    useEffect(() => {
        console.log('[DashboardEmbed] 🎬 MOUNTED with URL:', url);

        // Detect X-Frame-Options errors by checking if iframe fails to load
        const timer = setTimeout(() => {
            if (isLoading) {
                console.warn('[DashboardEmbed] ⚠️ Iframe taking too long to load, may be blocked by X-Frame-Options');
            }
        }, 5000);

        return () => {
            console.log('[DashboardEmbed] 💀 UNMOUNTING URL:', url);
            clearTimeout(timer);
        };
    }, []);

    useEffect(() => {
        console.log('[DashboardEmbed] 🔄 RE-RENDERED - URL changed to:', url);
    }, [url]);

    // ✅ GOOD - Use the URL as-is from backend (it's already signed or constructed correctly)
    const embedUrl = url;

    // Use a stable key based on resource ID, not the full embedUrl
    // This prevents re-mounting when the URL changes but it's the same resource
    const stableKey = `${resource.type}-${resource.id}`;
    console.log('[DashboardEmbed] 🔑 Using stable key:', stableKey, 'for URL:', embedUrl);

    return (
        <div className="mt-4 rounded-lg overflow-hidden border border-[#37393b] bg-[#1e1f20]">
            <div className="px-4 py-2 bg-[#2a2b2c] border-b border-[#37393b] flex items-center justify-between">
                <span className="text-sm text-gray-400">{resource.type === 'dashboard' ? 'Dashboard' : 'Explore'} Preview</span>
                <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                >
                    Open in Looker ↗
                </a>
            </div>
            <div className="relative" style={{ paddingBottom: '56.25%' }}>
                {embedError ? (
                    <div className="absolute top-0 left-0 w-full h-full flex flex-col items-center justify-center bg-[#1e1f20] p-8">
                        <div className="text-center max-w-md">
                            <div className="text-4xl mb-4">🔒</div>
                            <h3 className="text-lg font-semibold text-gray-200 mb-2">
                                Dashboard Cannot Be Embedded
                            </h3>
                            <p className="text-sm text-gray-400 mb-6">
                                This dashboard cannot be displayed in an iframe due to security settings (X-Frame-Options).
                                Please open it in a new tab to view.
                            </p>
                            <a
                                href={url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                            >
                                Open Dashboard in New Tab
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                            </a>
                        </div>
                    </div>
                ) : (
                    <iframe
                        key={stableKey}
                        src={embedUrl}
                        className="absolute top-0 left-0 w-full h-full"
                        frameBorder="0"
                        title={`${resource.type === 'dashboard' ? 'Dashboard' : 'Explore'} ${resource.id}`}
                        allowFullScreen
                        onLoad={() => {
                            console.log('[DashboardEmbed] ✅ iframe LOADED:', stableKey);
                            setIsLoading(false);
                        }}
                        onError={(e) => {
                            console.error('[DashboardEmbed] ❌ iframe ERROR:', e);
                            setEmbedError(true);
                            setIsLoading(false);
                        }}
                    />
                )}
            </div>
        </div>
    );
};

// Memoize to prevent unnecessary re-renders that cause flickering
export default React.memo(DashboardEmbed, (prevProps, nextProps) => {
    const same = prevProps.url === nextProps.url;
    console.log('[DashboardEmbed] 🧐 Memo check:', same ? '✅ SAME (skip re-render)' : '❌ DIFFERENT (will re-render)', {
        prevUrl: prevProps.url,
        nextUrl: nextProps.url,
    });
    return same;
});
