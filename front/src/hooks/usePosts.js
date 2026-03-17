import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchPostList } from "../api/postApi";

export default function usePosts(route) {
    const [posts, setPosts] = useState([]);
    const [activeTab, setActiveTab] = useState("latest");
    const [selectedCategory, setSelectedCategory] = useState("전체");

    const loadPosts = useCallback(async () => {
        try {
        const data = await fetchPostList();
        setPosts(Array.isArray(data) ? data : []);
        } catch (error) {
        console.log("게시글 불러오기 실패:", error);
        setPosts([]);
        }
    }, []);

    useEffect(() => {
        loadPosts();
    }, [loadPosts]);

    useEffect(() => {
        if (route?.params?.refresh || route?.params?.updatedPost) {
        loadPosts();
        }
    }, [route?.params?.refresh, route?.params?.updatedPost, loadPosts]);

    const filteredPosts = useMemo(() => {
        let result = Array.isArray(posts) ? [...posts] : [];

        if (selectedCategory !== "전체") {
        result = result.filter((post) => post.category === selectedCategory);
        }

        if (activeTab === "latest") {
        result.sort(
            (a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0)
        );
        }

        if (activeTab === "popular") {
        result.sort((a, b) => (b.likeCount || 0) - (a.likeCount || 0));
        }

        return result;
    }, [posts, activeTab, selectedCategory]);

    return {
        filteredPosts,
        activeTab,
        selectedCategory,
        setActiveTab,
        setSelectedCategory,
        reloadPosts: loadPosts, // [추가] 필요하면 화면에서 직접 재호출 가능
    };
    }