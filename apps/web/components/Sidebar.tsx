import { PlusCircle, MessageSquare, Menu, Settings as SettingsIcon, Trash2, Edit2, Check, X } from "lucide-react";
import GoogleAuth from "./GoogleAuth";
import { useState, useRef, useEffect } from "react";
import { SavedChat } from "../lib/userSettings";

interface SidebarProps {
    onNewChat: () => void;
    isOpen: boolean;
    toggleSidebar: () => void;
    onOpenSettings: () => void;
    onAuthChange?: (user: any | null) => void;
    savedChats: SavedChat[];
    currentChatId: string | null;
    onSelectChat: (chat: SavedChat) => void;
    onDeleteChat: (chatId: string) => void;
    onRenameChat: (chatId: string, newTitle: string) => void;
    exploreSelector?: React.ReactNode;
    isPocMode: boolean;
    onPocModeChange: (enabled: boolean) => void;
}

export default function Sidebar({
    onNewChat,
    isOpen,
    toggleSidebar,
    onOpenSettings,
    onAuthChange,
    savedChats,
    currentChatId,
    onSelectChat,
    onDeleteChat,
    onRenameChat,
    exploreSelector,
    isPocMode = false,
    onPocModeChange = () => { }
}: SidebarProps) {
    const [user, setUser] = useState<any | null>(null);
    const [editingChatId, setEditingChatId] = useState<string | null>(null);
    const [editTitle, setEditTitle] = useState("");
    const editInputRef = useRef<HTMLInputElement>(null);

    const handleUserChange = (newUser: any | null) => {
        setUser(newUser);
        onAuthChange?.(newUser);
    };

    useEffect(() => {
        if (editingChatId && editInputRef.current) {
            editInputRef.current.focus();
        }
    }, [editingChatId]);

    const startEditing = (e: React.MouseEvent, chat: SavedChat) => {
        e.stopPropagation();
        setEditingChatId(chat.id);
        setEditTitle(chat.title);
    };

    const saveEdit = (e: React.MouseEvent | React.FormEvent) => {
        e.stopPropagation();
        if (editingChatId && editTitle.trim()) {
            onRenameChat(editingChatId, editTitle.trim());
            setEditingChatId(null);
        }
    };

    const cancelEdit = (e: React.MouseEvent) => {
        e.stopPropagation();
        setEditingChatId(null);
    };

    const deleteChat = (e: React.MouseEvent, chatId: string) => {
        e.stopPropagation();
        if (confirm("Are you sure you want to delete this chat?")) {
            onDeleteChat(chatId);
        }
    };

    return (
        <div
            className={`
        fixed inset-y-0 left-0 z-50 bg-[#1e1f20] text-gray-200 transition-all duration-300 ease-in-out border-r border-[#37393b]
        ${isOpen ? "w-64" : "w-16"}
      `}
        >
            <div className="flex flex-col h-full">
                {/* Header */}
                <div className="flex items-center justify-between p-4 h-16">
                    <button
                        onClick={toggleSidebar}
                        className="p-2 hover:bg-[#37393b] rounded-full transition-colors"
                    >
                        <Menu className="w-5 h-5" />
                    </button>

                    {isOpen && (
                        <button
                            onClick={onNewChat}
                            className="p-2 bg-[#d3e3fd] text-[#041e49] rounded-full hover:bg-white transition-colors"
                            title="New Chat"
                        >
                            <PlusCircle className="w-5 h-5" />
                        </button>
                    )}
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto py-2 scrollbar-thin scrollbar-thumb-[#444746] scrollbar-track-transparent">

                    {/* Explore Selector & POC Toggle - Only when open */}
                    {isOpen && (
                        <div className="px-4 mb-6 space-y-4">
                            {/* Explore Selector */}
                            <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
                                Context
                            </div>
                            {exploreSelector}

                            {/* POC Mode Toggle */}
                            <div className="flex items-center justify-between bg-[#2A2B2D] p-3 rounded-lg border border-[#37393b]">
                                <div className="flex flex-col">
                                    <span className="text-sm font-medium text-white">POC Mode</span>
                                    <span className="text-[10px] text-gray-400">Restrict to Context</span>
                                </div>
                                <button
                                    onClick={() => onPocModeChange(!isPocMode)}
                                    className={`w-10 h-5 rounded-full transition-colors relative ${isPocMode ? 'bg-blue-500' : 'bg-gray-600'}`}
                                >
                                    <div className={`w-3 h-3 bg-white rounded-full absolute top-1 transition-transform ${isPocMode ? 'left-6' : 'left-1'}`} />
                                </button>
                            </div>
                        </div>
                    )}

                    {isOpen && (
                        <div className="px-4 mb-2 text-xs font-medium text-gray-400 uppercase tracking-wider">
                            Recent Chats
                        </div>
                    )}

                    <div className="space-y-1 px-2">
                        {savedChats.map((chat) => (
                            <div
                                key={chat.id}
                                onClick={() => !editingChatId && onSelectChat(chat)}
                                className={`
                  group w-full flex items-center p-3 rounded-lg hover:bg-[#37393b] transition-colors cursor-pointer
                  ${!isOpen ? "justify-center" : ""}
                  ${currentChatId === chat.id ? "bg-[#004a77] hover:bg-[#004a77]" : ""}
                `}
                            >
                                <MessageSquare className={`w-5 h-5 min-w-[20px] ${currentChatId === chat.id ? "text-[#a8c7fa]" : "text-gray-400"}`} />

                                {isOpen && (
                                    <div className="ml-3 flex-1 min-w-0 flex items-center justify-between">
                                        {editingChatId === chat.id ? (
                                            <div className="flex items-center w-full gap-1" onClick={e => e.stopPropagation()}>
                                                <input
                                                    ref={editInputRef}
                                                    type="text"
                                                    value={editTitle}
                                                    onChange={(e) => setEditTitle(e.target.value)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') saveEdit(e);
                                                        if (e.key === 'Escape') cancelEdit(e as any);
                                                    }}
                                                    className="w-full bg-[#131314] text-white px-1 py-0.5 rounded text-sm border border-[#4c8df6] focus:outline-none"
                                                />
                                                <button onClick={saveEdit} className="p-1 hover:text-green-400"><Check className="w-4 h-4" /></button>
                                                <button onClick={cancelEdit} className="p-1 hover:text-red-400"><X className="w-4 h-4" /></button>
                                            </div>
                                        ) : (
                                            <>
                                                <span className={`text-sm truncate ${currentChatId === chat.id ? "text-[#e3e3e3] font-medium" : "text-gray-300"}`}>
                                                    {chat.title}
                                                </span>

                                                {/* Actions */}
                                                <div className="hidden group-hover:flex items-center gap-1">
                                                    <button
                                                        onClick={(e) => startEditing(e, chat)}
                                                        className="p-1 text-gray-400 hover:text-white hover:bg-[#444746] rounded"
                                                        title="Rename"
                                                    >
                                                        <Edit2 className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button
                                                        onClick={(e) => deleteChat(e, chat.id)}
                                                        className="p-1 text-gray-400 hover:text-red-400 hover:bg-[#444746] rounded"
                                                        title="Delete"
                                                    >
                                                        <Trash2 className="w-3.5 h-3.5" />
                                                    </button>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))}

                        {savedChats.length === 0 && isOpen && (
                            <div className="px-4 py-8 text-center text-sm text-gray-500 italic">
                                No saved chats yet
                            </div>
                        )}
                    </div>
                </div>

                {/* Bottom Section - Settings and Auth */}
                <div className="mt-auto border-t border-[#37393b]">
                    {isOpen && (
                        <div className="p-4">
                            <GoogleAuth onAuthChange={handleUserChange} />
                        </div>
                    )}

                    <button
                        onClick={onOpenSettings}
                        className={`w-full flex items-center ${isOpen ? "gap-3 px-4" : "justify-center"
                            } py-4 hover:bg-[#37393b] transition-colors`}
                    >
                        <SettingsIcon className="w-5 h-5 flex-shrink-0" />
                        {isOpen && <span>Settings</span>}
                    </button>
                </div>
            </div>
        </div>
    );
}
