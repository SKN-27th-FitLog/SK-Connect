import { useEffect, useMemo, useState } from "react";
import { getPosts } from "../store/postStore";

export default function usePosts(route) {
    const [posts, setPosts] = useState(() => getPosts() ?? []);
    const [activeTab, setActiveTab] = useState("latest");
    const [selectedCategory, setSelectedCategory] = useState("전체");

    useEffect(() => {
        setPosts(getPosts() ?? []);
    }, []);

    useEffect(() => {
        if (route?.params?.newPost || route?.params?.updatedPost) {
        setPosts(getPosts() ?? []);
        }
    }, [route?.params?.newPost, route?.params?.updatedPost]);

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
    };
    }