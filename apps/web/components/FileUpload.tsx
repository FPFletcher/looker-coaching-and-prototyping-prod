import React, { useState, useEffect } from 'react';
import { X, ImageIcon, FileText, FileIcon } from 'lucide-react';

interface FileUploadProps {
    files: File[];
    onFilesChange: (files: File[]) => void;
    maxFiles?: number;
    acceptTypes?: string;
}

const FileUpload: React.FC<FileUploadProps> = ({
    files,
    onFilesChange,
    maxFiles = 5,
    acceptTypes = "image/*,.pdf,.doc,.docx,.txt,.csv,.json"
}) => {
    const [previews, setPreviews] = useState<{ url: string; type: string }[]>([]);

    // Sync previews with files prop - clear previews when files are cleared
    useEffect(() => {
        if (files.length === 0 && previews.length > 0) {
            // Revoke all object URLs to prevent memory leaks
            previews.forEach(preview => {
                if (preview.url.startsWith('blob:')) {
                    URL.revokeObjectURL(preview.url);
                }
            });
            setPreviews([]);
        }
    }, [files, previews]);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFiles = Array.from(e.target.files || []);

        // Limit total files
        const remainingSlots = maxFiles - files.length;
        const filesToAdd = selectedFiles.slice(0, remainingSlots);

        if (filesToAdd.length > 0) {
            const newFiles = [...files, ...filesToAdd];
            onFilesChange(newFiles);

            // Generate previews
            filesToAdd.forEach(file => {
                if (file.type.startsWith('image/')) {
                    // Image preview
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        setPreviews(prev => [...prev, { url: reader.result as string, type: 'image' }]);
                    };
                    reader.readAsDataURL(file);
                } else {
                    // File icon preview
                    setPreviews(prev => [...prev, { url: file.name, type: 'file' }]);
                }
            });
        }
    };

    const removeFile = (index: number) => {
        const newFiles = files.filter((_, i) => i !== index);
        const preview = previews[index];

        // Revoke object URL if it's a blob
        if (preview && preview.url.startsWith('blob:')) {
            URL.revokeObjectURL(preview.url);
        }

        const newPreviews = previews.filter((_, i) => i !== index);
        onFilesChange(newFiles);
        setPreviews(newPreviews);
    };

    const getFileIcon = (file: File) => {
        if (file.type.includes('pdf')) return <FileText className="w-5 h-5 text-red-400" />;
        if (file.type.includes('word') || file.type.includes('document')) return <FileText className="w-5 h-5 text-blue-400" />;
        if (file.type.includes('text')) return <FileText className="w-5 h-5 text-gray-400" />;
        return <FileIcon className="w-5 h-5 text-gray-400" />;
    };

    return (
        <div className="flex items-center gap-2">
            {/* File Previews */}
            {previews.map((preview, index) => (
                <div key={index} className="relative group">
                    {preview.type === 'image' ? (
                        // Image preview
                        <>
                            <img
                                src={preview.url}
                                alt={`Upload ${index + 1}`}
                                className="w-12 h-12 rounded-lg object-cover border border-[#37393b]"
                            />
                            <button
                                onClick={() => removeFile(index)}
                                className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                                title="Remove file"
                            >
                                <X className="w-3 h-3 text-white" />
                            </button>
                        </>
                    ) : (
                        // File icon preview
                        <div className="w-12 h-12 rounded-lg border border-[#37393b] bg-[#1E1F20] flex flex-col items-center justify-center relative">
                            {getFileIcon(files[index])}
                            <button
                                onClick={() => removeFile(index)}
                                className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                                title="Remove file"
                            >
                                <X className="w-3 h-3 text-white" />
                            </button>
                            <span className="text-[8px] text-gray-400 mt-0.5 truncate max-w-[40px]" title={files[index].name}>
                                {files[index].name.split('.').pop()?.toUpperCase()}
                            </span>
                        </div>
                    )}
                </div>
            ))}

            {/* Upload Button */}
            {files.length < maxFiles && (
                <label className="cursor-pointer">
                    <input
                        type="file"
                        accept={acceptTypes}
                        multiple
                        onChange={handleFileSelect}
                        className="hidden"
                    />
                    <div className="w-12 h-12 rounded-lg border-2 border-dashed border-[#37393b] hover:border-blue-500 flex items-center justify-center transition-colors">
                        <ImageIcon className="w-5 h-5 text-gray-500" />
                    </div>
                </label>
            )}
        </div>
    );
};

export default FileUpload;
