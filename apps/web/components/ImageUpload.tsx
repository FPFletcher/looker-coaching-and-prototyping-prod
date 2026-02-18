import React, { useState, useEffect } from 'react';
import { X, ImageIcon } from 'lucide-react';

interface ImageUploadProps {
    images: File[];
    onImagesChange: (images: File[]) => void;
    maxImages?: number;
}

const ImageUpload: React.FC<ImageUploadProps> = ({ images, onImagesChange, maxImages = 5 }) => {
    const [previews, setPreviews] = useState<string[]>([]);

    // Sync previews with images prop - clear previews when images are cleared
    useEffect(() => {
        if (images.length === 0) {
            setPreviews([]);
        }
    }, [images]);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || []);
        const imageFiles = files.filter(file => file.type.startsWith('image/'));

        // Limit total images
        const remainingSlots = maxImages - images.length;
        const filesToAdd = imageFiles.slice(0, remainingSlots);

        if (filesToAdd.length > 0) {
            const newImages = [...images, ...filesToAdd];
            onImagesChange(newImages);

            // Generate previews
            filesToAdd.forEach(file => {
                const reader = new FileReader();
                reader.onloadend = () => {
                    setPreviews(prev => [...prev, reader.result as string]);
                };
                reader.readAsDataURL(file);
            });
        }
    };

    const removeImage = (index: number) => {
        const newImages = images.filter((_, i) => i !== index);
        const newPreviews = previews.filter((_, i) => i !== index);
        onImagesChange(newImages);
        setPreviews(newPreviews);
    };

    return (
        <div className="flex items-center gap-2">
            {/* Image Previews */}
            {previews.map((preview, index) => (
                <div key={index} className="relative group">
                    <img
                        src={preview}
                        alt={`Upload ${index + 1}`}
                        className="w-12 h-12 rounded-lg object-cover border border-[#37393b]"
                    />
                    <button
                        onClick={() => removeImage(index)}
                        className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                        title="Remove image"
                    >
                        <X className="w-3 h-3 text-white" />
                    </button>
                </div>
            ))}

            {/* Upload Button */}
            {images.length < maxImages && (
                <label className="cursor-pointer">
                    <input
                        type="file"
                        accept="image/*"
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

export default ImageUpload;
