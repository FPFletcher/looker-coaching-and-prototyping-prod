import React, { useEffect } from 'react';

interface DashboardEmbedProps {
    url: string;
}

const DashboardEmbed: React.FC<DashboardEmbedProps> = ({ url }) => {
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

    // DEBUG: Log when this component mounts/unmounts/re-renders
    useEffect(() => {
        console.log('[DashboardEmbed] 🎬 MOUNTED with URL:', url);
        return () => {
            console.log('[DashboardEmbed] 💀 UNMOUNTING URL:', url);
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
                <iframe
                    key={stableKey}
                    src={embedUrl}
                    className="absolute top-0 left-0 w-full h-full"
                    frameBorder="0"
                    title={`${resource.type === 'dashboard' ? 'Dashboard' : 'Explore'} ${resource.id}`}
                    allowFullScreen
                    onLoad={() => {
                        console.log('[DashboardEmbed] ✅ iframe LOADED:', stableKey);
                    }}
                    onError={(e) => {
                        console.error('[DashboardEmbed] ❌ iframe ERROR:', e);
                    }}
                />
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
