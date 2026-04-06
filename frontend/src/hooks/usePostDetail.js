import { useEffect, useMemo, useState } from "react";
import { fetchPostDetail } from "../api/postApi";

export default function usePostDetail(initialPost) {
    const [post, setPost] = useState(
        initialPost || {
        id: "",
        author: "익명",
        authorBadge: "익",
        createdAt: "",
        title: "",
        content: "",
        imageUrl: "",
        likeCount: 0,
        liked: false,
        category: "",
        location: "",
        comments: [],
        }
    );

    const [liked, setLiked] = useState(initialPost?.liked ?? false);
    const [likeCount, setLikeCount] = useState(initialPost?.likeCount ?? 0);
    const [comments, setComments] = useState(initialPost?.comments ?? []);
    const [commentText, setCommentText] = useState("");

    useEffect(() => {
        const loadDetail = async () => {
        try {
            if (!initialPost?.id) return;

            const detailData = await fetchPostDetail(initialPost.id);

            setPost((prev) => ({
            ...prev,
            ...detailData,
            }));

            setLiked(detailData?.liked ?? initialPost?.liked ?? false);
            setLikeCount(detailData?.likeCount ?? initialPost?.likeCount ?? 0);
            setComments(detailData?.comments ?? initialPost?.comments ?? []);
        } catch (error) {
            console.log("게시글 상세 불러오기 실패:", error);
        }
        };

        loadDetail();
    }, [initialPost]);

    const handleLikePress = () => {
        setLiked((prev) => {
        const nextLiked = !prev;
        setLikeCount((prevCount) =>
            nextLiked ? prevCount + 1 : Math.max(prevCount - 1, 0)
        );
        return nextLiked;
        });
    };

    const handleSubmitComment = () => {
        const text = commentText.trim();
        if (!text) return;

        const newComment = {
        id: Date.now().toString(),
        author: "나",
        authorBadge: "나",
        content: text,
        createdAt: new Date().toISOString(),
        };

        setComments((prev) => [...prev, newComment]);
        setCommentText("");
    };

    const updatedPost = useMemo(() => {
        return {
        ...post,
        liked,
        likeCount,
        comments,
        commentCount: comments.length,
        };
    }, [post, liked, likeCount, comments]);

    return {
        post,
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