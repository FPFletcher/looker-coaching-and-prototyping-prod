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
    // Just pass the URL through - logic is simplified
    return <DashboardEmbed url={url} />;
};

export default React.memo(StableDashboardEmbed, (prevProps, nextProps) => {
    const same = prevProps.url === nextProps.url;
    console.log('[StableDashboardEmbed] 🧐 Memo check:', same ? '✅ SAME' : '❌ DIFFERENT', {
        prevUrl: prevProps.url,
        nextUrl: nextProps.url,
    });
    return same;
});
