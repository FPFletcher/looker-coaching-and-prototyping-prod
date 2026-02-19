import React, { useRef, useEffect, useMemo, memo, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import { Loader2, ChevronDown, Terminal, CheckCircle2, SendHorizontal, Image as ImageIcon, Mic, Sparkles, Copy, Check } from "lucide-react";
import ThinkingBlock from "./ThinkingBlock";
import StableDashboardEmbed from "./StableDashboardEmbed";
import FileUpload from "./FileUpload";
import remarkGfm from "remark-gfm";
import { getCurrentUser } from "../lib/userSettings";

const CopyButton = ({ content }: { content: string }) => {
    const [copied, setCopied] = React.useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error("Failed to copy", err);
        }
    };

    return (
        <button
            onClick={handleCopy}
            className="p-1.5 text-[#8E918F] hover:text-[#E3E3E3] hover:bg-[#333537] rounded-md transition-colors"
            title="Copy response"
        >
            {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
        </button>
    );
};

interface ToolStep {
    tool: string;
    input?: any;
    result?: any;
    status: "running" | "success" | "error";
    error?: string;
}

interface ToolPart {
    type: 'tool';
    tool: string;
    input?: any;
    result?: any;
    status: "running" | "success" | "error";
    error?: string;
}

interface TextPart {
    type: 'text';
    content: string;
}

export type MessagePart = ToolPart | TextPart;

export interface Message {
    id?: string; // Stable ID for React keys - CRITICAL for preventing re-renders
    role: "user" | "assistant";
    content: string; // Keep for backward compat / simple text
    parts?: MessagePart[]; // New field for interleaved content
    thinkingSteps?: ToolStep[]; // Keep for backward compat
    isThinking?: boolean;
    images?: string[]; // Base64 image data for display
    files?: { name: string; type: string; data: string }[]; // File attachments
}

interface ChatInterfaceProps {
    messages: Message[];
    isLoading: boolean;
    inputValue: string;
    setInputValue: (val: string) => void;
    onSubmit: (e: React.FormEvent) => void;
    messagesEndRef: React.RefObject<HTMLDivElement>;
    mode?: 'existing' | 'dummy';
    selectedImages: File[];
    onImagesChange: (images: File[]) => void;
    onStop?: () => void;
}

const ChatInterface = memo(function ChatInterface({
    messages,
    isLoading,
    inputValue,
    setInputValue,
    onSubmit,
    messagesEndRef,
    mode = 'existing',
    selectedImages,
    onImagesChange
}: ChatInterfaceProps) {
    const { onStop } = arguments[0];

    // Log when component re-renders


    // Helper to determine which logo to show based on active tool
    const getLogoForMessage = useCallback((msg: Message) => {
        if (!msg.thinkingSteps || msg.thinkingSteps.length === 0) {
            return '/selo-logo.jpg';
        }

        // Check the most recent tool
        const lastTool = msg.thinkingSteps[msg.thinkingSteps.length - 1];
        if (lastTool.tool === 'search_web') {
            return '/google-logo.svg';
        } else if (lastTool.tool && (lastTool.tool.includes('toolbox') || lastTool.tool.includes('mcp'))) {
            return '/adk-logo.svg';
        }
        return '/selo-logo.jpg';
    }, []);

    useEffect(() => {
        // Auto-resize textarea
        const textarea = document.getElementById('chat-textarea');
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        }
    }, [inputValue]);

    // Dynamic Greeting Logic (Top-Level)
    const [greeting, setGreeting] = React.useState("Hello there!");
    useEffect(() => {
        const user = getCurrentUser();
        if (user?.name) {
            setGreeting(`Hi ${user.name.split(' ')[0]}`);
        }
    }, []);

    // Dynamic prompts... (omitted for brevity, keep existing)
    const prompts = mode === 'existing'
        ? [
            { icon: Terminal, text: "Create a dashboard for sales metrics" },
            { icon: Sparkles, text: "Analyze order trends over time" },
            { icon: ImageIcon, text: "Show me available data models" }
        ]
        : [
            { icon: Sparkles, text: "Create a full retail analytics prototype" },
            { icon: Terminal, text: "Build an e-commerce demo dashboard" },
            { icon: ImageIcon, text: "Generate sample data reports" }
        ];

    const handlePromptClick = useCallback((promptText: string) => {
        setInputValue(promptText);
    }, [setInputValue]);

    // Memoize markdown components to prevent re-creation on every render
    const markdownComponents = useMemo(() => ({
        a: ({ node, ...props }: any) => {
            const href = props.href || "";
            // Support both standard dashboards, explores, and embed URLs
            const isEmbeddable = href.includes("/dashboards/") || href.includes("/explore/") || href.includes("looker.app/embed/");

            console.log('[ChatInterface] 🔗 Processing Link:', { href, isEmbeddable });

            if (isEmbeddable) {
                let embedUrl = href;
                // If it's a standard URL, convert to embed
                if (!href.includes("/embed/")) {
                    console.log('[ChatInterface] 🔄 Converting standard URL to Embed URL');
                    if (href.includes("/dashboards/")) {
                        embedUrl = href.replace("/dashboards/", "/embed/dashboards/");
                    } else if (href.includes("/explore/")) {
                        embedUrl = href.replace("/explore/", "/embed/explore/");
                    }
                } else {
                    console.log('[ChatInterface] ✅ Already an Embed URL');
                }

                console.log('[ChatInterface] 🚀 Final Embed URL:', embedUrl);

                return (
                    <span className="block my-4">
                        <a {...props} className="text-[#A8C7FA] hover:underline block mb-2" target="_blank" rel="noreferrer">
                            {props.children}
                        </a>
                        <StableDashboardEmbed url={embedUrl} />
                    </span>
                );
            }
            return <a {...props} className="text-[#A8C7FA] hover:underline" target="_blank" rel="noreferrer" />;
        },
        p: ({ node, ...props }: any) => <div className="mb-4 last:mb-0" {...props} />,
        ul: ({ node, ...props }: any) => <ul className="list-disc pl-5 mb-4 space-y-1" {...props} />,
        ol: ({ node, ...props }: any) => <ol className="list-decimal pl-5 mb-4 space-y-1" {...props} />,
        code: ({ node, ...props }: any) => <code className="bg-[#2A2B2D] px-1.5 py-0.5 rounded text-[#E2E2E2] font-mono text-sm" {...props} />,
        pre: ({ node, ...props }: any) => <pre className="bg-[#1E1F20] p-4 rounded-xl border border-[#333537] overflow-x-auto mb-4" {...props} />,
    }), []);

    const renderMarkdown = useCallback((content: string) => (
        <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={markdownComponents}
        >
            {content}
        </ReactMarkdown>
    ), [markdownComponents]);


    return (
        <div className="flex flex-col h-full bg-gradient-to-br from-[#131314] to-[#0a1929] text-[#E3E3E3] relative">

            {/* Messages Area - Responsive Padding */}
            <div className="flex-1 overflow-y-auto px-4 md:px-8 lg:px-12 py-6 md:py-8 space-y-6 md:space-y-8 scrollbar-thin scrollbar-thumb-[#444746] scrollbar-track-transparent">
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-start justify-center max-w-4xl mx-auto -mt-12 md:-mt-20 px-2">
                        <div className="mb-2">
                            <Sparkles className="w-12 h-12 text-[#4c8df6]" />
                        </div>
                        <h1 className="text-4xl md:text-6xl font-medium tracking-tight bg-gradient-to-r from-[#4c8df6] via-[#9c5af2] to-[#e47672] bg-clip-text text-transparent pb-4">
                            {greeting}
                        </h1>
                        <h2 className="text-4xl md:text-6xl font-medium text-[#444746] tracking-tight">
                            Where should we start?
                        </h2>
                    </div>
                )}


                {useMemo(() => {

                    return messages.map((msg, idx) => {
                        // Use stable ID if available (CRITICAL for preventing re-renders during streaming!)
                        const msgKey = msg.id || `fallback-${idx}`;
                        return (
                            <div key={msgKey} className={`flex w-full ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                                <div className={`max-w-6xl w-full ${msg.role === "user" ? "bg-[#333537] rounded-[24px] px-6 py-4 rounded-tr-md" : "pr-6"}`}>
                                    {/* Assistant Avatar for AI messages */}
                                    {msg.role === "assistant" && (
                                        <div className="flex items-start justify-between mb-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-full overflow-hidden shrink-0">
                                                    <img
                                                        src={getLogoForMessage(msg)}
                                                        alt="AI"
                                                        className={`w-full h-full object-cover ${msg.isThinking ? 'animate-pulse' : ''}`}
                                                    />
                                                </div>
                                            </div>
                                            {!msg.isThinking && (
                                                <CopyButton content={msg.content} />
                                            )}
                                        </div>
                                    )}

                                    {/* Render Interleaved Parts if available, otherwise fallback to thinking + content */}
                                    {msg.parts && msg.parts.length > 0 ? (
                                        <div className="space-y-4">
                                            {msg.parts.map((part, pIdx) => (
                                                <div key={pIdx}>
                                                    {part.type === 'tool' ? (
                                                        <ThinkingBlock
                                                            tool={{
                                                                name: part.tool,
                                                                input: part.input,
                                                                output: part.result || part.error,
                                                                status: part.status,
                                                            }}
                                                        />
                                                    ) : (
                                                        <div className="prose prose-invert max-w-none text-[#E3E3E3] text-[16px] leading-relaxed">
                                                            {renderMarkdown(part.content)}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <>
                                            {/* Display attached images for user messages */}
                                            {msg.role === "user" && msg.images && msg.images.length > 0 && (
                                                <div className="flex flex-wrap gap-2 mb-3">
                                                    {msg.images.map((img, imgIdx) => (
                                                        <img
                                                            key={imgIdx}
                                                            src={img}
                                                            alt={`Attachment ${imgIdx + 1}`}
                                                            className="max-w-xs max-h-64 rounded-lg border border-[#444746] object-cover"
                                                        />
                                                    ))}
                                                </div>
                                            )}

                                            {/* Legacy Rendering Fallback */}
                                            {msg.role === "assistant" && msg.thinkingSteps && msg.thinkingSteps.length > 0 && (
                                                <div className="mb-4 space-y-2">
                                                    {msg.thinkingSteps.map((step, stepsIdx) => (
                                                        <ThinkingBlock
                                                            key={stepsIdx}
                                                            tool={{
                                                                name: step.tool,
                                                                input: step.input,
                                                                output: step.result || step.error,
                                                                status: step.status,
                                                            }}
                                                        />
                                                    ))}
                                                </div>
                                            )}
                                            <div className="prose prose-invert max-w-none text-[#E3E3E3] text-[16px] leading-relaxed">
                                                {renderMarkdown(msg.content)}
                                            </div>
                                        </>
                                    )}
                                </div>
                            </div>
                        );
                    });
                }, [messages])}

                {/* Loader for simple text wait (if thinking accordion not enough) */}
                {isLoading && messages.length > 0 && !messages[messages.length - 1].isThinking && (
                    <div className="flex items-center gap-2 text-[#C4C7C5] animate-pulse pl-2">
                        <div className="w-2 h-2 rounded-full bg-[#E3E3E3]"></div>
                        <div className="w-2 h-2 rounded-full bg-[#E3E3E3]"></div>
                        <div className="w-2 h-2 rounded-full bg-[#E3E3E3]"></div>
                    </div>
                )}

                <div ref={messagesEndRef} className="h-4" />
            </div>

            {/* Input Area (Bottom Floating) - Transparent Gradient Background */}
            <div className="p-3 md:p-4 lg:p-6 sticky bottom-0 z-10 bg-gradient-to-t from-[#131314] via-[#131314]/95 to-transparent">
                <div className="max-w-4xl mx-auto space-y-3 md:space-y-4">

                    {/* Suggestion Chips (only on empty state) */}
                    {messages.length === 0 && (
                        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide snap-x snap-mandatory -mx-4 px-4 md:mx-0 md:px-0">
                            {prompts.map((prompt, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => handlePromptClick(prompt.text)}
                                    className="whitespace-nowrap flex items-center gap-2 px-4 py-3 min-h-[44px] bg-[#1E1F20] hover:bg-[#333537] rounded-xl text-[#E3E3E3] border border-[#333537] transition-colors text-sm snap-start"
                                >
                                    <prompt.icon className="w-4 h-4 text-[#C4C7C5]" />
                                    {prompt.text}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Main Input Box */}
                    <div className="relative rounded-[28px] bg-[#1E1F20] transition-colors focus-within:bg-[#2A2B2D]">
                        <form onSubmit={onSubmit}>
                            <textarea
                                id="chat-textarea"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        onSubmit(e);
                                    }
                                }}
                                placeholder="Ask Selo"
                                className="w-full bg-transparent text-[#E3E3E3] p-4 md:p-5 pr-12 md:pr-14 rounded-[28px] focus:outline-none resize-none min-h-[56px] max-h-[200px] placeholder-[#8E918F] text-[16px] leading-relaxed"
                                rows={1}
                            />

                            <div className="absolute right-4 bottom-3 flex items-center gap-2">
                                {/* Image Upload and Action Buttons */}
                                <div className="flex items-center gap-1">
                                    <FileUpload
                                        files={selectedImages}
                                        onFilesChange={onImagesChange}
                                        maxFiles={3}
                                    />
                                </div>

                                {/* Send Button */}
                                {isLoading && onStop ? (
                                    <button
                                        type="button"
                                        onClick={onStop}
                                        className="p-2 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
                                        title="Stop generating"
                                    >
                                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                            <rect x="6" y="6" width="8" height="8" />
                                        </svg>
                                    </button>
                                ) : inputValue.trim() && (
                                    <button
                                        type="submit"
                                        disabled={isLoading}
                                        className="p-2 bg-[#E3E3E3] text-[#131314] rounded-full hover:bg-white transition-colors disabled:opacity-50"
                                    >
                                        {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <SendHorizontal className="w-5 h-5" />}
                                    </button>
                                )}
                            </div>
                        </form>
                    </div>

                    <div className="text-center text-[11px] text-[#8E918F]">
                        Selo may display inaccurate info, including about people, so double-check its responses.
                    </div>
                </div>
            </div>
        </div>
    );
});

ChatInterface.displayName = 'ChatInterface';

export default ChatInterface;
