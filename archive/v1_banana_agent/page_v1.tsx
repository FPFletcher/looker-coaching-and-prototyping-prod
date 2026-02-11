"use client";

import { useState, useRef } from "react";
import { Upload, Sparkles, Loader2, Image as ImageIcon, Database, ArrowRight } from "lucide-react";
import clsx from "clsx";

export default function Home() {
    const [prompt, setPrompt] = useState("");
    const [file, setFile] = useState<File | null>(null);
    const [connectionName, setConnectionName] = useState("ffrancois_-_ecomm_trial");
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Configuration State
    const [lookerUrl, setLookerUrl] = useState("https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app");
    const [clientId, setClientId] = useState("vQyY8tbjsT6tcG7ZV85N");
    const [clientSecret, setClientSecret] = useState("hyPbyWkJXDz8h6tGcYk5Y44G");
    const [status, setStatus] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
        }
    };

    const handleSubmit = async () => {
        if (!prompt) return;
        setIsSubmitting(true);
        setStatus("Thinking...");

        try {
            const formData = new FormData();
            formData.append("prompt", prompt);
            formData.append("connection_name", connectionName || "thelook");
            formData.append("looker_url", lookerUrl);
            formData.append("client_id", clientId);
            formData.append("client_secret", clientSecret);
            if (file) formData.append("file", file);

            const response = await fetch('http://localhost:8000/api/generate_prototype', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) throw new Error("Failed to generate");

            const data = await response.json();
            console.log(data);
            setStatus("Prototype Generated!");
            setTimeout(() => setIsSubmitting(false), 2000);
        } catch (e) {
            console.error(e);
            setStatus("Error generating prototype");
            setIsSubmitting(false);
        }
    };

    return (
        <main className="flex flex-col min-h-screen bg-white relative">

            {/* Top Nav / Branding */}
            <div className="p-6 flex items-center justify-between">
                <div className="flex items-center gap-2 text-gray-600">
                    <span className="font-medium text-lg">Banana Agent</span>
                    <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 text-xs font-medium">Experiment</span>
                </div>
                <div className="w-8 h-8 rounded-full bg-gray-200 overflow-hidden">
                    {/* User Avatar Placeholder */}
                    <div className="w-full h-full bg-gradient-to-tr from-blue-400 to-purple-400"></div>
                </div>
            </div>

            {/* Main Content Area - Centered */}
            <div className="flex-1 flex flex-col items-center justify-center p-4 max-w-4xl mx-auto w-full space-y-12 -mt-20">

                {/* Greeting */}
                <div className="text-center w-full space-y-6">
                    <h1 className="text-6xl font-medium tracking-tight">
                        <span className="gemini-text-gradient">Hello, François</span>
                    </h1>
                    <h2 className="text-5xl font-normal text-gray-300">
                        What should we build today?
                    </h2>

                    {/* Configuration Section */}
                    <details className="w-full max-w-2xl mx-auto text-left bg-white/50 backdrop-blur-sm rounded-xl p-4 border border-gray-100">
                        <summary className="cursor-pointer text-gray-500 font-medium hover:text-gray-700 transition-colors">
                            ⚙️ Looker Configuration (Required for verified execution)
                        </summary>
                        <div className="grid grid-cols-1 gap-4 mt-4">
                            <div>
                                <label className="block text-xs font-medium text-gray-500 mb-1">Looker Instance URL</label>
                                <input
                                    type="text"
                                    className="w-full p-2 rounded-lg border border-gray-200 text-sm focus:ring-2 focus:ring-blue-100 outline-none"
                                    placeholder="https://your-instance.looker.com"
                                    value={lookerUrl}
                                    onChange={(e) => setLookerUrl(e.target.value)}
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-medium text-gray-500 mb-1">Client ID</label>
                                    <input
                                        type="text"
                                        className="w-full p-2 rounded-lg border border-gray-200 text-sm focus:ring-2 focus:ring-blue-100 outline-none"
                                        placeholder="Client ID"
                                        value={clientId}
                                        onChange={(e) => setClientId(e.target.value)}
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-500 mb-1">Client Secret</label>
                                    <input
                                        type="password"
                                        className="w-full p-2 rounded-lg border border-gray-200 text-sm focus:ring-2 focus:ring-blue-100 outline-none"
                                        placeholder="Client Secret"
                                        value={clientSecret}
                                        onChange={(e) => setClientSecret(e.target.value)}
                                    />
                                </div>
                            </div>
                        </div>
                    </details>
                </div>
            </div>

            {/* Input Area (Gemini Style) */}
            <div className="w-full bg-[#f0f4f9] rounded-[32px] p-6 transition-all duration-300 ease-in-out focus-within:bg-white focus-within:shadow-2xl focus-within:ring-2 focus-within:ring-blue-100/50">

                <textarea
                    className="w-full bg-transparent border-none outline-none text-lg text-gray-800 placeholder-gray-500 min-h-[120px] resize-none p-2"
                    placeholder="Describe your Looker prototype (e.g. Sales Dashboard for EMEA)..."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                />

                {/* Attachments / Options Row */}
                <div className="flex items-center justify-between mt-4 px-2">
                    <div className="flex items-center gap-2">
                        {/* Upload Button */}
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            className={clsx("p-2 rounded-full hover:bg-gray-200 transition-colors tooltip flex items-center gap-2", file && "bg-blue-100 text-blue-700")}
                            title="Upload ERD"
                        >
                            <ImageIcon className="w-5 h-5" />
                            {file && <span className="text-xs font-medium max-w-[100px] truncate">{file.name}</span>}
                        </button>
                        <input type="file" ref={fileInputRef} className="hidden" accept="image/*" onChange={handleFileChange} />

                        {/* Connection Config */}
                        <div className="relative group">
                            <div className="flex items-center gap-2 bg-white rounded-full px-3 py-1.5 border border-gray-200 text-sm text-gray-600">
                                <Database className="w-4 h-4" />
                                <input
                                    type="text"
                                    className="outline-none w-32 bg-transparent placeholder-gray-400"
                                    placeholder="Connection..."
                                    value={connectionName}
                                    onChange={(e) => setConnectionName(e.target.value)}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Submit Button */}
                    <button
                        onClick={handleSubmit}
                        disabled={!prompt || isSubmitting}
                        className={clsx(
                            "w-10 h-10 flex items-center justify-center rounded-full transition-all duration-300",
                            prompt ? "bg-black text-white hover:bg-gray-800" : "bg-gray-200 text-gray-400 cursor-not-allowed"
                        )}
                    >
                        {isSubmitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowRight className="w-5 h-5" />}
                    </button>
                </div>
            </div>

            {/* Suggestion Chips */}
            {!prompt && (
                <div className="flex gap-4 overflow-x-auto w-full pb-2">
                    {["Retail Sales Dashboard", "Customer Churn Analysis", "Supply Chain ERD to LookML"].map((suggestion) => (
                        <button
                            key={suggestion}
                            onClick={() => setPrompt(suggestion)}
                            className="flex-shrink-0 px-6 py-3 bg-[#f0f4f9] hover:bg-[#e1e5ea] rounded-xl text-sm font-medium text-gray-700 transition-colors"
                        >
                            {suggestion}
                        </button>
                    ))}
                </div>
            )}

            {/* Status Message */}
            {status && (
                <div className="flex items-center gap-2 text-blue-600 animate-in fade-in slide-in-from-bottom-4">
                    <Sparkles className="w-4 h-4" />
                    <span className="font-medium">{status}</span>
                </div>
            )}

        </main>
    );
}
