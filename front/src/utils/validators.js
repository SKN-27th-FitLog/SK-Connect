export function validatePostForm({ title, content, category }) {
    if (!title?.trim()) return "제목을 입력해주세요.";
    if (!content?.trim()) return "내용을 입력해주세요.";
    if (!category?.trim()) return "카테고리를 선택해주세요.";
    return "";
}