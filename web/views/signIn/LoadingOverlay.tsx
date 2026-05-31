interface LoadingOverlayProps {
  isLoading: boolean;
}

export const LoadingOverlay = ({ isLoading }: LoadingOverlayProps) => {
  if (!isLoading) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex flex-col items-center justify-center gap-4 bg-[#fffdf8]/95 backdrop-blur-sm">
      <div className="h-12 w-12 animate-spin rounded-full border-4 border-[#eee4d7] border-t-[#b77519]" />
      <p className="text-base font-medium text-[#6f665c]">Đang đăng nhập...</p>
    </div>
  );
};
