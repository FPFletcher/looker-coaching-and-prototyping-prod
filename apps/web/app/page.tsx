"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Sidebar from "../components/Sidebar";
import ChatInterface, { MessagePart } from "@/components/ChatInterface";
import type { Message } from "@/components/ChatInterface";
import SettingsModal, { SettingsData, LookerCredentials } from "../components/SettingsModal";
import ExploreSelector from "../components/ExploreSelector";
import { getUserSetting, saveUserSetting } from "@/lib/userSettings";

interface Explore {
    name: string;
    label: string;
    model: string;
}

import {
    clearUserSettings,
    clearAnonymousSettings,
    GoogleUser,
    SavedChat,
    saveChat,
    getSavedChats,
    deleteChat,
    renameChat,
    StoredMessage
} from "../lib/userSettings";

export default function Home() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [sessionId, setSessionId] = useState(() => Math.random().toString(36).substring(7));
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [mode, setMode] = useState<'existing' | 'dummy'>('existing');
    const [selectedModel, setSelectedModel] = useState('claude-sonnet-4-5-20250929');
    const [selectedExplore, setSelectedExplore] = useState<Explore | null>(null);
    const [abortController, setAbortController] = useState<AbortController | null>(null);
    const [currentUser, setCurrentUser] = useState<GoogleUser | null>(null);
    const [selectedImages, setSelectedImages] = useState<File[]>([]);

    // Chat History State
    const [savedChats, setSavedChats] = useState<SavedChat[]>([]);
    const [currentChatId, setCurrentChatId] = useState<string | null>(null);

    // Default credentials
    const defaultCredentials: LookerCredentials = {
        url: "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app",
        client_id: "vQyY8tbjsT6tcG7ZV85N",
        client_secret: "hyPbyWkJXDz8h6tGcYk5Y44G"
    };

    const [credentials, setCredentials] = useState<LookerCredentials>(defaultCredentials);

    // Load user, settings, and chats on mount
    useEffect(() => {
        if (typeof window !== 'undefined') {
            // Try to get current user
            const userStr = localStorage.getItem('google_user');
            let userId: string | undefined;
            if (userStr) {
                try {
                    const user = JSON.parse(userStr) as GoogleUser;
                    userId = user.id;
                    setCurrentUser(user);

                    // Load saved chats for user
                    setSavedChats(getSavedChats(user.id));
                } catch (e) {
                    console.error('Failed to parse user:', e);
                }
            }

            // Load settings with user scope
            const settings = getUserSetting<SettingsData>('looker_settings', userId);
            if (settings) {
                setCredentials(settings.credentials);
                setMode(settings.mode || 'existing');
                setSelectedModel(settings.model || 'claude-sonnet-4-5-20250929');
            }
        }
    }, []); // Run once on mount

    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoading]);

    // Auto-save chat effect
    useEffect(() => {
        if (messages.length > 0 && currentUser) {
            const saveTimeout = setTimeout(() => {
                const chatId = currentChatId || sessionId;

                // Determine title
                let title = "New Chat";
                if (currentChatId) {
                    // Keep existing title if editing
                    const existing = savedChats.find(c => c.id === currentChatId);
                    if (existing) title = existing.title;
                } else if (messages.length > 0) {
                    // Generate title from first user message
                    const firstUserMsg = messages.find(m => m.role === "user");
                    if (firstUserMsg) {
                        title = firstUserMsg.content.slice(0, 30) + (firstUserMsg.content.length > 30 ? "..." : "");
                    }
                }

                const chatToSave: SavedChat = {
                    id: chatId,
                    title: title,
                    messages: messages.map(m => ({
                        role: m.role,
                        content: m.content,
                        parts: m.parts,
                        thinkingSteps: m.thinkingSteps
                    })),
                    updatedAt: Date.now()
                };

                saveChat(chatToSave, currentUser.id);
                setSavedChats(getSavedChats(currentUser.id));

                // If this was a new chat, update currentChatId
                if (!currentChatId) {
                    setCurrentChatId(chatId);
                }
            }, 1000); // 1s debounce

            return () => clearTimeout(saveTimeout);
        }
    }, [messages, currentChatId, currentUser, sessionId]); // savedChats excluded to avoid loops

    const handleNewChat = () => {
        setMessages([]);
        setInput("");
        setCurrentChatId(null);
        setSessionId(Math.random().toString(36).substring(7));
    };

    const handleSelectChat = (chat: SavedChat) => {
        setMessages(chat.messages.map(m => ({
            id: `loaded-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`, // Generate ID for loaded messages
            role: m.role,
            content: m.content,
            parts: m.parts,
            thinkingSteps: m.thinkingSteps,
            isThinking: false
        })));
        setCurrentChatId(chat.id);
        setSessionId(chat.id); // Reuse chat ID as session ID

        // Mobile sidebar close might be good here if we had mobile state
    };

    const handleDeleteChat = (chatId: string) => {
        if (currentUser) {
            deleteChat(chatId, currentUser.id);
            setSavedChats(getSavedChats(currentUser.id));
            if (currentChatId === chatId) {
                handleNewChat();
            }
        }
    };

    const handleRenameChat = (chatId: string, newTitle: string) => {
        if (currentUser) {
            renameChat(chatId, newTitle, currentUser.id);
            setSavedChats(getSavedChats(currentUser.id));
        }
    };

    const handleSaveSettings = (settings: SettingsData) => {
        setCredentials(settings.credentials);
        setMode(settings.mode);
        setSelectedModel(settings.model);

        // Save to scoped localStorage
        if (typeof window !== 'undefined') {
            saveUserSetting('looker_settings', settings, currentUser?.id);
        }
    };

    // Handle user authentication changes
    const handleAuthChange = (user: GoogleUser | null) => {
        setCurrentUser(user);

        if (user) {
            // User logged in - load their settings and chats
            const userSettings = getUserSetting<SettingsData>('looker_settings', user.id);
            if (userSettings) {
                setCredentials(userSettings.credentials);
                setMode(userSettings.mode || 'existing');
                setSelectedModel(userSettings.model || 'claude-sonnet-4-5-20250929');
            }
            setSavedChats(getSavedChats(user.id));

            // Clear anonymous settings
            clearAnonymousSettings();
        } else {
            // User logged out
            setSavedChats([]);
            handleNewChat();

            // Load anonymous settings or use defaults
            const anonSettings = getUserSetting<SettingsData>('looker_settings');
            if (anonSettings) {
                setCredentials(anonSettings.credentials);
                setMode(anonSettings.mode || 'existing');
                setSelectedModel(anonSettings.model || 'claude-sonnet-4-5-20250929');
            } else {
                // Reset to defaults
                setCredentials({
                    url: "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app",
                    client_id: "vQyY8tbjsT6tcG7ZV85N",
                    client_secret: "hyPbyWkJXDz8h6tGcYk5Y44G"
                });
                setMode('existing');
                setSelectedModel('claude-sonnet-4-5-20250929');
            }
        }
    };

    const handleSubmit = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMessage = input.trim();
        setInput("");

        // Add user message with stable ID
        const userMsgId = `user-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
        setMessages((prev) => [...prev, { id: userMsgId, role: "user", content: userMessage }]);
        setIsLoading(true);
        setSelectedImages([]); // Clear images after sending

        // Add assistant "thinking" placeholder with stable ID that won't change
        const assistantMsgId = `assistant-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
        setMessages((prev) => [
            ...prev,
            { id: assistantMsgId, role: "assistant", content: "", isThinking: true, thinkingSteps: [], parts: [] },
        ]);

        try {
            // Create abort controller for this request
            const controller = new AbortController();
            setAbortController(controller);
            // Convert images to base64
            const imagePromises = selectedImages.map(file => {
                return new Promise<string>((resolve) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result as string);
                    reader.readAsDataURL(file);
                });
            });
            const base64Images = await Promise.all(imagePromises);

            const response = await fetch("http://localhost:8000/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: userMessage,
                    conversation_history: messages
                        .filter(m => !m.isThinking) // Don't send thinking placeholders
                        .map((m) => ({
                            role: m.role,
                            content: m.content,
                            // Include parts for full context (tool calls + responses)
                            parts: m.parts
                        })),
                    credentials: credentials,
                    model: selectedModel,
                    session_id: sessionId,
                    explore: selectedExplore, // Send selected explore
                    images: base64Images,      // Send images as base64
                    gcp_project: getUserSetting<SettingsData>('looker_settings', currentUser?.id)?.gcpProject,
                    gcp_location: getUserSetting<SettingsData>('looker_settings', currentUser?.id)?.gcpLocation
                }),
                signal: controller.signal // Add abort signal
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body?.getReader();
            if (!reader) throw new Error("No reader available");

            const decoder = new TextDecoder();
            let buffer = "";
            let currentParts: MessagePart[] = [];
            let currentTextBuffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (!line.trim() || !line.startsWith("data: ")) continue;

                    try {
                        const data = JSON.parse(line.slice(6));

                        // Handle tool_start
                        if (data.type === "tool_use" || data.type === "tool_start") {
                            // If we have pending text, push it as a part first
                            if (currentTextBuffer) {
                                currentParts.push({ type: 'text', content: currentTextBuffer });
                                currentTextBuffer = "";
                            }
                            // Then add the tool part
                            currentParts.push({
                                type: 'tool',
                                tool: data.tool_name || data.tool,
                                input: data.tool_input || data.input,
                                status: "running",
                            });
                        }
                        // Handle tool_end / result
                        else if (data.type === "tool_result" || data.type === "tool_end") {
                            const toolName = data.tool_name || data.tool;
                            // Find the *last* matching running tool to update
                            for (let i = currentParts.length - 1; i >= 0; i--) {
                                if (currentParts[i].type === 'tool' && (currentParts[i] as any).tool === toolName && (currentParts[i] as any).status === 'running') {
                                    (currentParts as any)[i] = {
                                        ...currentParts[i],
                                        result: data.result,
                                        status: "success"
                                    };
                                    break;
                                }
                            }
                        }
                        // Handle text
                        else if (data.type === "text") {
                            currentTextBuffer += data.content;
                        }
                        // Handle error
                        else if (data.type === "error") {
                            currentTextBuffer += `\nError: ${data.content}`;
                        }

                        // Update state
                        setMessages((prev) => {
                            const updated = [...prev];
                            const lastMsg = updated[updated.length - 1];
                            if (lastMsg.role === "assistant") {
                                const displayParts = [...currentParts];
                                if (currentTextBuffer) {
                                    displayParts.push({ type: 'text', content: currentTextBuffer });
                                }

                                lastMsg.parts = displayParts;
                                // Legacy fallback
                                lastMsg.content = displayParts.filter(p => p.type === 'text').map(p => p.content || '').join('');
                                lastMsg.thinkingSteps = displayParts.filter(p => p.type === 'tool') as any[];
                                lastMsg.isThinking = false;
                            }
                            return updated;
                        });

                    } catch (e) {
                        console.error("Error parsing SSE line:", line, e);
                    }
                }
            }
        } catch (error) {
            console.error("Chat error:", error);
            setMessages((prev) => {
                const updated = [...prev];
                const lastMsg = updated[updated.length - 1];
                if (lastMsg.role === "assistant") {
                    lastMsg.content = `Error: ${error instanceof Error ? error.message : "Unknown error"}`;
                    lastMsg.isThinking = false;
                }
                return updated;
            });
        } finally {
            setIsLoading(false);
            setAbortController(null);
        }
    }, [input, isLoading, credentials, mode, selectedModel, selectedExplore, selectedImages, currentUser, currentChatId, sessionId]);

    const handleStop = useCallback(() => {
        if (abortController) {
            abortController.abort();
            setAbortController(null);
            setIsLoading(false);

            // Update last message to show it was stopped
            setMessages((prev) => {
                const updated = [...prev];
                const lastMsg = updated[updated.length - 1];
                if (lastMsg && lastMsg.role === "assistant" && lastMsg.isThinking) {
                    lastMsg.content = "Response stopped by user.";
                    lastMsg.isThinking = false;
                }
                return updated;
            });
        }
    }, [abortController]);

    return (
        <div className="flex h-screen bg-[#131314]">
            <Sidebar
                isOpen={isSidebarOpen}
                toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
                onNewChat={handleNewChat}
                onOpenSettings={() => setIsSettingsOpen(true)}
                onAuthChange={handleAuthChange}
                savedChats={savedChats}
                currentChatId={currentChatId}
                onSelectChat={handleSelectChat}
                onDeleteChat={handleDeleteChat}
                onRenameChat={handleRenameChat}
            />

            <main className={`flex-1 transition-all duration-300 ${isSidebarOpen ? "ml-64" : "ml-16"} h-full flex flex-col`}>
                {/* Explore Selector - Always visible */}
                <div className="px-40 pt-6 pb-4 border-b border-[#37393b]">
                    <ExploreSelector
                        lookerUrl={credentials.url}
                        clientId={credentials.client_id}
                        clientSecret={credentials.client_secret}
                        onSelectExplore={setSelectedExplore}
                        selectedExplore={selectedExplore}
                    />
                </div>

                <div className="flex-1">
                    <ChatInterface
                        messages={messages}
                        isLoading={isLoading}
                        inputValue={input}
                        setInputValue={setInput}
                        onSubmit={handleSubmit}
                        messagesEndRef={messagesEndRef}
                        mode={mode}
                        selectedImages={selectedImages}
                        onImagesChange={setSelectedImages}
                        onStop={handleStop}
                    />
                </div>
            </main>

            <SettingsModal
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
                onSave={handleSaveSettings}
                initialSettings={{ credentials, mode, model: selectedModel }}
            />
        </div>
    );
}
