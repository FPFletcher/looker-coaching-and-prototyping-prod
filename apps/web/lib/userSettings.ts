/**
 * User Settings Storage Utility
 * 
 * Provides scoped localStorage management to isolate settings per user.
 * Anonymous and authenticated users have separate settings namespaces.
 */

export interface GoogleUser {
    id: string;
    email: string;
    name?: string;
    picture?: string;
}

/**
 * Get the scoped key for a setting based on user authentication
 */
function getScopedKey(key: string, userId?: string): string {
    if (userId) {
        return `setting_user_${userId}_${key}`;
    }
    return `setting_anonymous_${key}`;
}

/**
 * Save a user setting with proper scoping
 */
export function saveUserSetting(key: string, value: any, userId?: string): void {
    try {
        const scopedKey = getScopedKey(key, userId);
        const serialized = JSON.stringify(value);
        localStorage.setItem(scopedKey, serialized);
    } catch (error) {
        console.error('Failed to save user setting:', error);
    }
}

/**
 * Get a user setting with proper scoping
 */
export function getUserSetting<T>(key: string, userId?: string, defaultValue?: T): T | null {
    try {
        const scopedKey = getScopedKey(key, userId);
        const item = localStorage.getItem(scopedKey);

        if (item === null) {
            return defaultValue ?? null;
        }

        return JSON.parse(item) as T;
    } catch (error) {
        console.error('Failed to get user setting:', error);
        return defaultValue ?? null;
    }
}

/**
 * Clear all settings for a specific user
 */
export function clearUserSettings(userId: string): void {
    try {
        const prefix = `setting_user_${userId}_`;
        const keysToRemove: string[] = [];

        // Find all keys for this user
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(prefix)) {
                keysToRemove.push(key);
            }
        }

        // Remove them
        keysToRemove.forEach(key => localStorage.removeItem(key));

        console.log(`Cleared ${keysToRemove.length} settings for user ${userId}`);
    } catch (error) {
        console.error('Failed to clear user settings:', error);
    }
}

/**
 * Clear all anonymous settings
 */
export function clearAnonymousSettings(): void {
    try {
        const prefix = 'setting_anonymous_';
        const keysToRemove: string[] = [];

        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(prefix)) {
                keysToRemove.push(key);
            }
        }

        keysToRemove.forEach(key => localStorage.removeItem(key));

        console.log(`Cleared ${keysToRemove.length} anonymous settings`);
    } catch (error) {
        console.error('Failed to clear anonymous settings:', error);
    }
}

/**
 * Migrate existing unscoped settings to user-scoped settings
 * This is called when a user logs in for the first time
 */
export function migrateToUserSettings(userId: string, settingsToMigrate: string[]): void {
    try {
        settingsToMigrate.forEach(key => {
            const unscopedValue = localStorage.getItem(key);
            if (unscopedValue) {
                // Save to user-scoped key
                const userKey = getScopedKey(key, userId);
                localStorage.setItem(userKey, unscopedValue);

                // Remove unscoped key
                localStorage.removeItem(key);
            }
        });

        console.log(`Migrated ${settingsToMigrate.length} settings for user ${userId}`);
    } catch (error) {
        console.error('Failed to migrate settings:', error);
    }
}

/**
 * Get the current user from localStorage
 */
export function getCurrentUser(): GoogleUser | null {
    try {
        const userStr = localStorage.getItem('google_user');
        if (userStr) {
            return JSON.parse(userStr) as GoogleUser;
        }
        return null;
    } catch (error) {
        console.error('Failed to get current user:', error);
        return null;
    }
}

// Chat Persistence Types
export interface StoredMessage {
    role: "user" | "assistant";
    content: string;
    parts?: any[];
    thinkingSteps?: any[];
}

export interface SavedChat {
    id: string;
    title: string;
    messages: StoredMessage[];
    updatedAt: number;
}

/**
 * Get all saved chats for a user
 */
export function getSavedChats(userId: string): SavedChat[] {
    try {
        const key = getScopedKey('saved_chats', userId);
        const item = localStorage.getItem(key);
        if (!item) return [];
        return JSON.parse(item) as SavedChat[];
    } catch (error) {
        console.error('Failed to get saved chats:', error);
        return [];
    }
}

/**
 * Save or update a chat
 */
export function saveChat(chat: SavedChat, userId: string): void {
    try {
        const chats = getSavedChats(userId);
        const existingIndex = chats.findIndex(c => c.id === chat.id);

        if (existingIndex >= 0) {
            chats[existingIndex] = chat;
        } else {
            chats.unshift(chat); // Add new chats to top
        }

        // Sort by updatedAt desc
        chats.sort((a, b) => b.updatedAt - a.updatedAt);

        const key = getScopedKey('saved_chats', userId);
        localStorage.setItem(key, JSON.stringify(chats));
    } catch (error) {
        console.error('Failed to save chat:', error);
    }
}

/**
 * Rename a chat
 */
export function renameChat(chatId: string, newTitle: string, userId: string): void {
    try {
        const chats = getSavedChats(userId);
        const chat = chats.find(c => c.id === chatId);
        if (chat) {
            chat.title = newTitle;
            chat.updatedAt = Date.now(); // Update timestamp

            const key = getScopedKey('saved_chats', userId);
            localStorage.setItem(key, JSON.stringify(chats));
        }
    } catch (error) {
        console.error('Failed to rename chat:', error);
    }
}

/**
 * Delete a chat
 */
export function deleteChat(chatId: string, userId: string): void {
    try {
        const chats = getSavedChats(userId);
        const filtered = chats.filter(c => c.id !== chatId);

        const key = getScopedKey('saved_chats', userId);
        localStorage.setItem(key, JSON.stringify(filtered));
    } catch (error) {
        console.error('Failed to delete chat:', error);
    }
}
