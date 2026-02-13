export const getApiUrl = () => {
    // Check if we are in a browser environment
    if (typeof window !== 'undefined') {
        // Allow overriding via environment variable
        if (process.env.NEXT_PUBLIC_API_URL) {
            return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, ""); // Remove trailing slash if present
        }
    }
    // Default to localhost for development
    return 'http://localhost:8000';
};
