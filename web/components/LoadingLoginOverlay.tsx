interface LoadingOverlayProps {
  isLoading: boolean;
}

export const LoadingOverlay = ({ isLoading }: LoadingOverlayProps) => {
  if (!isLoading) return null;

  return (
    <div className="fixed inset-0 bg-white flex items-center justify-center flex-col gap-6 z-[9999]">
      {/* Spinner với animation đẹp */}
      <div className="relative">
        <div className="w-16 h-16 border-4 border-gray-200 border-t-indigo-600 rounded-full animate-spin"></div>
        <div
          className="absolute inset-0 w-16 h-16 border-4 border-transparent border-r-indigo-400 rounded-full animate-spin"
          style={{
            animationDirection: "reverse",
            animationDuration: "1.5s",
          }}
        ></div>
      </div>
      {/* Text loading */}
      <div className="text-center space-y-2">
        <p className="text-gray-700 text-lg font-medium">Loading...</p>
        <p className="text-gray-500 text-sm">Please wait...</p>
      </div>
    </div>
  );
};
