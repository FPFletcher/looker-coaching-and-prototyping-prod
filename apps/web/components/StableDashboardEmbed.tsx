import React, { useMemo, useEffect } from 'react';
import DashboardEmbed from './DashboardEmbed';

interface StableDashboardEmbedProps {
    url: string;
}

/**
 * Wrapper that extracts and stabilizes the lookerBaseUrl prop
 * to prevent unnecessary re-renders of the DashboardEmbed iframe
 */
const StableDashboardEmbed: React.FC<StableDashboardEmbedProps> = ({ url }) => {
    // Extract base URL once and memoize it based on the URL  
    const baseUrl = useMemo(() => {
        const extracted = url.split(/\/dashboards\/|\/embed\/|\/explore\//)[0];
        console.log('[StableDashboardEmbed] 🔗 Extracted baseUrl:', extracted, 'from URL:', url);
        return extracted;
    }, [url]);

    useEffect(() => {
        console.log('[StableDashboardEmbed] 🎬 MOUNTED with URL:', url);
    }, []);

    return <DashboardEmbed url={url} lookerBaseUrl={baseUrl} />;
};

export default React.memo(StableDashboardEmbed, (prevProps, nextProps) => {
    const same = prevProps.url === nextProps.url;
    console.log('[StableDashboardEmbed] 🧐 Memo check:', same ? '✅ SAME' : '❌ DIFFERENT', {
        prevUrl: prevProps.url,
        nextUrl: nextProps.url,
    });
    return same;
});
