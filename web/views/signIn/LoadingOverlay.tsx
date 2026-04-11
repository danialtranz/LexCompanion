interface LoadingOverlayProps {
    isLoading: boolean;
}

export const LoadingOverlay = ({ isLoading }: LoadingOverlayProps) => {
    if (!isLoading) return null;

    return (
        <div className="fixed inset-0 bg-white/95 backdrop-blur-sm flex items-center justify-center flex-col gap-4 z-[9999]">
            <div className="w-12 h-12 border-4 border-gray-200 border-t-indigo-600 rounded-full animate-spin"></div>
            <p className="text-gray-600 text-base font-medium">Đang đăng nhập...</p>
        </div>
    );
};
