import React, { useState, useEffect, useRef } from 'react';
import { LogOut } from 'lucide-react';

interface GoogleAuthProps {
    onAuthChange: (user: GoogleUser | null) => void;
}

interface GoogleUser {
    id: string;
    email: string;
    name?: string;
    picture?: string;
}

declare global {
    interface Window {
        google: any;
    }
}

const GoogleAuth: React.FC<GoogleAuthProps> = ({ onAuthChange }) => {
    const [user, setUser] = useState<GoogleUser | null>(null);
    const [loading, setLoading] = useState(true);
    const buttonRef = useRef<HTMLDivElement>(null);

    // Hardcoded Client ID (fallback for NEXT_PUBLIC env var)
    const CLIENT_ID = "826056756274-7653f7jteulh4en41u5oiupqe2stur2s.apps.googleusercontent.com";
    const [scriptLoaded, setScriptLoaded] = useState(false);

    // Load Google SDK once on mount
    useEffect(() => {
        const script = document.createElement('script');
        script.src = 'https://accounts.google.com/gsi/client';
        script.async = true;
        script.defer = true;

        script.onload = () => {
            setScriptLoaded(true);
        };

        document.body.appendChild(script);

        return () => {
            if (document.body.contains(script)) {
                document.body.removeChild(script);
            }
        };
    }, []);

    // Load saved user on mount
    useEffect(() => {
        const savedUser = localStorage.getItem('google_user');
        if (savedUser) {
            try {
                const parsedUser = JSON.parse(savedUser) as GoogleUser;
                setUser(parsedUser);
                onAuthChange(parsedUser);
            } catch (e) {
                console.error('Failed to parse saved user:', e);
            }
        }
        setLoading(false);
    }, []);

    // Render Google button when logged out and script is loaded
    useEffect(() => {
        if (!scriptLoaded || user || loading) {
            return; // Don't render if script not loaded, user logged in, or still loading
        }

        if (window.google && buttonRef.current) {
            // Clear any existing button
            if (buttonRef.current) {
                buttonRef.current.innerHTML = '';
            }

            // Initialize Google Sign-In
            window.google.accounts.id.initialize({
                client_id: CLIENT_ID,
                callback: handleCredentialResponse,
                auto_select: false,
            });

            // Render the Google Sign-In button
            window.google.accounts.id.renderButton(
                buttonRef.current,
                {
                    theme: 'outline',
                    size: 'large',
                    width: 250,
                    text: 'signin_with',
                }
            );
        }
    }, [user, scriptLoaded, loading]); // Re-render when user state changes

    const handleCredentialResponse = async (response: any) => {
        try {
            console.log('Received credential response from Google');

            // Send token to backend for verification
            const res = await fetch('http://localhost:8000/api/auth/google', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: response.credential }),
            });

            if (res.ok) {
                const userData = await res.json();
                console.log('Backend verification successful:', userData);

                setUser(userData.user);
                localStorage.setItem('google_user', JSON.stringify(userData.user));
                localStorage.setItem('auth_token', response.credential);
                onAuthChange(userData.user);
            } else {
                const errorData = await res.json().catch(() => ({ error: 'Unknown error' }));
                console.error('Backend verification failed:', errorData);
                alert('Authentication failed. Please try again.');
            }
        } catch (error) {
            console.error('Authentication error:', error);
            alert('Authentication failed. Please check your connection and try again.');
        }
    };

    const handleSignOut = () => {
        setUser(null);
        localStorage.removeItem('google_user');
        localStorage.removeItem('auth_token');
        onAuthChange(null);

        if (window.google) {
            window.google.accounts.id.disableAutoSelect();
        }
    };

    if (loading) {
        return null;
    }

    if (user) {
        return (
            <div className="flex items-center gap-3 px-4 py-2 bg-[#2a2b2c] rounded-lg border border-[#37393b]">
                {user.picture && (
                    <img
                        src={user.picture}
                        alt={user.name || user.email}
                        className="w-8 h-8 rounded-full"
                    />
                )}
                <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-white truncate">
                        {user.name || user.email}
                    </div>
                    <div className="text-xs text-gray-400 truncate">{user.email}</div>
                </div>
                <button
                    onClick={handleSignOut}
                    className="p-2 hover:bg-[#333537] rounded-lg transition-colors"
                    title="Sign out"
                >
                    <LogOut className="w-4 h-4 text-gray-400" />
                </button>
            </div>
        );
    }

    // Render Google's button container
    return (
        <div
            ref={buttonRef}
            className="w-full"
            style={{ minHeight: '40px' }}
        />
    );
};

export default GoogleAuth;
