export const Terms = () => {
    return (
        <div className="text-center mt-6 text-xs text-gray-400 leading-relaxed">
            <span>
                Bằng cách đăng nhập, bạn đồng ý với
            </span>
            <a
                href="#terms"
                className="text-indigo-600 hover:text-indigo-700 hover:underline transition-colors"
            >
                {" "}Điều khoản dịch vụ
            </a>
            <span> và</span>
            <a
                href="#privacy"
                className="text-indigo-600 hover:text-indigo-700 hover:underline transition-colors"
            >
                {" "}Chính sách bảo mật
            </a>
        </div>
    );
};
