import { useMemo, useState } from "react";

export default function usePostDetail(initialPost) {
    const [liked, setLiked] = useState(initialPost?.liked ?? false);
    const [likeCount, setLikeCount] = useState(initialPost?.likeCount ?? 0);
    const [comments, setComments] = useState(initialPost?.comments ?? []);
    const [commentText, setCommentText] = useState("");

    const handleLikePress = () => {
        setLiked((prev) => !prev);
        setLikeCount((prev) => (liked ? prev - 1 : prev + 1));
    };

    const handleSubmitComment = () => {
        const text = commentText.trim();
        if (!text) return;

        const newComment = {
        id: Date.now().toString(),
        author: "나",
        content: text,
        createdAt: new Date().toISOString(),
        };

        setComments((prev) => [newComment, ...prev]);
        setCommentText("");
    };

    const updatedPost = useMemo(() => {
        return {
        ...initialPost,
        liked,
        likeCount,
        comments,
        commentCount: comments.length,
        };
    }, [initialPost, liked, likeCount, comments]);

    return {
        liked,
        likeCount,
        comments,
        commentText,
        setCommentText,
        handleLikePress,
        handleSubmitComment,
        updatedPost,
    };
    }